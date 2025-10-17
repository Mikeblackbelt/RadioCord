import discord
from discord.ext import commands
from discord import app_commands
from yt_dlp import YoutubeDL
import asyncio

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extract_flat': False
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}


class YouTube(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = '2.0'
        self.music_queues = {}  # guild_id -> list of (title, url, page_url)
        self.currently_playing = {}  # guild_id -> song info
        self.play_locks = {}  # guild_id -> asyncio.Lock()

    async def play_next(self, interaction: discord.Interaction):
        """Play the next song in queue automatically."""
        guild_id = interaction.guild.id
        queue = self.music_queues.get(guild_id, [])

        if not queue:
            vc = interaction.guild.voice_client
            if vc and vc.is_connected():
                await asyncio.sleep(3)
                await vc.disconnect()
            return

        next_song = queue.pop(0)
        self.currently_playing[guild_id] = next_song

        vc = interaction.guild.voice_client
        if not vc:
            channel = interaction.user.voice.channel
            vc = await channel.connect()

        title, url, page_url = next_song

        def after_playback(e):
            if e:
                print(f"Error during playback: {e}")
            asyncio.run_coroutine_threadsafe(self.play_next(interaction), self.bot.loop)

        vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), after=after_playback)

        embed = discord.Embed(
            title="Now Playing (YouTube)",
            description=f"[{title}]({page_url})",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

    async def add_to_queue(self, interaction: discord.Interaction, query: str):
        """Fetch and queue a song."""
        with YoutubeDL(YDL_OPTIONS) as ydl:
            search_query = query if query.startswith("http") else f"ytsearch:{query}"
            info = ydl.extract_info(search_query, download=False)
            if "entries" in info:
                info = info["entries"][0]
            url = info["url"]
            title = info.get("title", "Unknown")
            page_url = info.get("webpage_url", query)

        guild_id = interaction.guild.id
        self.music_queues.setdefault(guild_id, []).append((title, url, page_url))
        return title, page_url

    @app_commands.command(name="playyt", description="Add a YouTube song to the queue or start playing.")
    async def playyt(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            await interaction.followup.send("You’re not in a voice channel.", ephemeral=True)
            return

        title, page_url = await self.add_to_queue(interaction, query)
        guild_id = interaction.guild.id

        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await self.play_next(interaction)
        else:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Added to Queue",
                    description=f"[{title}]({page_url})",
                    color=discord.Color.blue()
                )
            )

    @app_commands.command(name="queue", description="View the current music queue.")
    async def queue(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        queue = self.music_queues.get(guild_id, [])
        if not queue:
            await interaction.response.send_message("The queue is empty.")
            return

        description = "\n".join([f"{i+1}. [{t}]({u})" for i, (t, _, u) in enumerate(queue[:10])])
        embed = discord.Embed(title="🎶 Current Queue", description=description, color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="skip", description="Skip the current song.")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message("Nothing is currently playing.")
            return

        vc.stop()
        await interaction.response.send_message("⏭️ Skipped!")

    @app_commands.command(name="remove", description="Remove a song from the queue by index.")
    async def remove(self, interaction: discord.Interaction, index: int):
        guild_id = interaction.guild.id
        queue = self.music_queues.get(guild_id, [])
        if 0 < index <= len(queue):
            removed = queue.pop(index - 1)
            await interaction.response.send_message(f"🗑️ Removed **{removed[0]}** from queue.")
        else:
            await interaction.response.send_message("Invalid index.")


async def setup(bot):
    cog = YouTube(bot)
    await bot.add_cog(cog)
    embed = discord.Embed(title=f'YT Cog Successfully loaded', description=f'Version: {cog.version}\nCommands: {cog.get_app_commands()}')
    update = bot.get_channel(1428731822442811403)
    if update:
        await update.send(embed=embed)
