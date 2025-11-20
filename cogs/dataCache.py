# history_collector_one_time.py
import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
import asyncio
import datetime
import sqlite3
from typing import Optional

PROGRESS_FILE = "progress.json"
DB_FILE = "messages.db"
# timezone-aware UTC cutoff
CUTOFF_DATE = datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)


# -------------------------------
# Database init
# -------------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER UNIQUE,
            guild TEXT,
            channel TEXT,
            author TEXT,
            content TEXT,
            timestamp TEXT
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_id ON messages(message_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_guild_channel ON messages(guild, channel)")

    conn.commit()
    conn.close()


# -------------------------------
# Progress utils
# -------------------------------
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}


def save_progress(data):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, indent=2)


# -------------------------------
# The collector Cog (one-time archival)
# -------------------------------
class HistoryCollector(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.progress = load_progress()
        self.queue: list[tuple[int, int]] = []
        self.task_started = False

        # Counters for summary
        self.inserted_count = 0
        self.channels_processed = 0
        self.forbidden_count = 0

        init_db()
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()

    # ---------------------------
    # DB insert with retry
    # ---------------------------
    async def insert_message(self, msg: discord.Message, guild_name: str, channel_name: str):
        for attempt in range(4):
            try:
                self.cursor.execute("""
                    INSERT INTO messages (message_id, guild, channel, author, content, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    msg.id,
                    guild_name,
                    channel_name,
                    getattr(msg.author, "name", str(msg.author)),
                    msg.content,
                    msg.created_at.isoformat()
                ))
                self.conn.commit()
                self.inserted_count += 1
                return
            except sqlite3.IntegrityError:
                # Already exists; not an error
                return
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower():
                    await asyncio.sleep(0.1 * (attempt + 1))
                else:
                    raise

    # ---------------------------
    # Build queue
    # ---------------------------
    def build_queue(self):
        self.queue.clear()
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                self.queue.append((guild.id, channel.id))

    # ---------------------------
    # Self-healing fetch
    # ---------------------------
    async def fetch_messages_safe(self, channel: discord.TextChannel, before_id: Optional[int]):
        kwargs = {"limit": 100}
        if before_id:
            kwargs["before"] = discord.Object(id=before_id)

        try:
            msgs = [m async for m in channel.history(**kwargs)]
        except discord.Forbidden:
            raise
        except Exception:
            msgs = []

        if msgs:
            return msgs

        # Nothing returned; if no pointer, truly empty
        if not before_id:
            return []

        # Try to repair by probing backwards exponentially
        print(f"[REPAIR] {channel.guild.name}/{channel.name}: bad before_id {before_id}, attempting repair...")
        step = 50
        probe = before_id

        for attempt in range(20):
            probe -= step
            if probe < 1:
                break
            try:
                probe_msgs = [m async for m in channel.history(limit=10, before=discord.Object(id=probe))]
            except discord.Forbidden:
                raise
            except Exception:
                probe_msgs = []

            if probe_msgs:
                print(f"[REPAIR] {channel.guild.name}/{channel.name}: repair succeeded at probe id {probe_msgs[0].id}")
                return probe_msgs

            step *= 2

        print(f"[REPAIR-END] {channel.guild.name}/{channel.name}: repair failed; treating as no more messages.")
        return []

    # ---------------------------
    # One-time collector loop
    # ---------------------------
    @tasks.loop(seconds=0.5)
    async def collect_task(self):
        # If nothing in queue, stop and print summary.
        if not self.queue:
            print("[ARCHIVE] queue empty, finishing archive pass.")
            await self.finish_archive()
            return

        guild_id, channel_id = self.queue[0]
        guild = self.bot.get_guild(guild_id)
        if not guild:
            # If bot left guild or guild not available, skip
            print(f"[ARCHIVE] guild {guild_id} not available; skipping.")
            self.queue.pop(0)
            self.channels_processed += 1
            return

        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            print(f"[ARCHIVE] channel {channel_id} not a text channel or not available; skipping.")
            self.queue.pop(0)
            self.channels_processed += 1
            return

        channel_key = f"{guild_id}-{channel_id}"
        before_id = self.progress.get(channel_key)

        try:
            msgs = await self.fetch_messages_safe(channel, before_id)

            if not msgs:
                # Nothing exists before pointer -> channel finished
                print(f"[DONE] {guild.name}/{channel.name}: fully processed or empty.")
                self.queue.pop(0)
                self.channels_processed += 1
                # Save progress to persist final state
                save_progress(self.progress)
                return

            # Process returned messages oldest-first: history returns newest-first,
            # but we are stepping backwards so the list is newest->oldest.
            for msg in msgs:
                if msg.created_at <= CUTOFF_DATE:
                    print(f"[CUT] {guild.name}/{channel.name}: cutoff reached.")
                    self.queue.pop(0)
                    self.channels_processed += 1
                    save_progress(self.progress)
                    break

                await self.insert_message(msg, guild.name, channel.name)

                # update progress immediately
                self.progress[channel_key] = msg.id
                save_progress(self.progress)

                # rate control to keep api happy; target ~15 msg/sec
                await asyncio.sleep(0.03)

        except discord.Forbidden:
            print(f"[SKIP] {guild.name}/{channel.name}: 403 Forbidden (Missing Access).")
            self.queue.pop(0)
            self.forbidden_count += 1
            save_progress(self.progress)
            return
        except Exception as e:
            # Unexpected error: log and sleep briefly, then continue (we don't pop the channel)
            print(f"[ERROR] {guild.name}/{channel.name}: unexpected error: {e}")
            await asyncio.sleep(2)
            return

    @collect_task.before_loop
    async def before_collect(self):
        await self.bot.wait_until_ready()

    # ---------------------------
    # Finish summary
    # ---------------------------
    async def finish_archive(self):
        # Stop the loop if it's running
        if self.collect_task.is_running():
            self.collect_task.stop()

        print("==== ARCHIVE SUMMARY ====")
        print(f"Messages inserted: {self.inserted_count}")
        print(f"Channels processed: {self.channels_processed}")
        print(f"Channels forbidden: {self.forbidden_count}")
        print("=========================")
        # Ensure progress saved
        save_progress(self.progress)

    # ---------------------------
    # Commands: start, status, reset
    # ---------------------------
    @commands.Cog.listener()
    async def on_ready(self):
        if not self.task_started:
            print("Building queue and starting one-time history collector...")
            self.build_queue()
            self.collect_task.start()
            self.task_started = True

    @app_commands.command(name='start-archive', description='Start a one-time archival pass now.')
    async def start_archive(self, interaction: discord.Interaction):
        if self.collect_task.is_running():
            await interaction.response.send_message("Archive already running.")
            return
        self.build_queue()
        # reset counters so summary reflects fresh run
        self.inserted_count = 0
        self.channels_processed = 0
        self.forbidden_count = 0
        self.collect_task.start()
        await interaction.response.send_message("Started one-time archival pass.")

    @app_commands.command(name='status', description='Show message collection status')
    async def status(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Queue remaining: {len(self.queue)}\n"
            f"Messages inserted this run: {self.inserted_count}\n"
            f"Channels processed this run: {self.channels_processed}\n"
            f"Forbidden channels this run: {self.forbidden_count}\n"
            f"Saved progress entries: {len(self.progress)}"
        )

    @app_commands.command(name='reset-progress', description='Reset progress for a guild-channel key, or all if none provided.')
    @app_commands.describe(channel_key="Provide guildid-channelid (e.g. 12345-67890). Leave empty to clear everything.")
    async def reset_progress(self, interaction: discord.Interaction, channel_key: Optional[str] = None):
        if interaction.user.id != 928109349140824125: 
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        
        if channel_key:
            if channel_key in self.progress:
                self.progress.pop(channel_key, None)
                save_progress(self.progress)
                await interaction.response.send_message(f"Removed progress for {channel_key}.")
            else:
                await interaction.response.send_message(f"No progress entry for {channel_key}.")
            return

        # clear everything
        self.progress.clear()
        save_progress(self.progress)
        await interaction.response.send_message("Cleared all progress entries. Archive will start from channel start on next run.")

# -------------------------------
# Cog setup
# -------------------------------
async def setup(bot: commands.Bot):
    await bot.add_cog(HistoryCollector(bot))
