import discord
from discord.ext import commands
from discord import app_commands
from yt_dlp import YoutubeDL
import asyncio
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_music')

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
        self.version = '2.4'
        self.music_queues = {}  # guild_id -> list of (title, url, page_url)
        self.currently_playing = {}  # guild_id -> song info
        self.text_channels = {}  # guild_id -> text channel for sending messages

    async def play_next(self, guild_id: int):
        """Play the next song in the queue"""
        logger.info(f"play_next called for guild {guild_id}")
        
        await asyncio.sleep(0.5)  # Small delay to let things settle
        
        queue = self.music_queues.get(guild_id, [])
        guild = self.bot.get_guild(guild_id)
        
        if not guild:
            logger.error(f"Guild {guild_id} not found")
            return

        if not queue:
            logger.info(f"Queue empty for guild {guild_id}")
            vc = guild.voice_client
            if vc and vc.is_connected():
                await asyncio.sleep(3)
                try:
                    await vc.disconnect()
                except:
                    pass
            return

        next_song = queue.pop(0)
        self.currently_playing[guild_id] = next_song
        title, url, page_url = next_song
        logger.info(f"Preparing to play: {title}")

        vc = guild.voice_client
        if not vc or not vc.is_connected():
            logger.error(f"Voice client not connected for guild {guild_id}")
            return

        # Determine the file to play
        file_to_play = url
        if title.endswith((".mp4", ".mp3")):
            file_to_play = os.path.abspath(url)
            logger.info(f"Playing local file: {file_to_play}")
            if not os.path.exists(file_to_play):
                logger.error(f"Local file does not exist: {file_to_play}")
                text_channel = self.text_channels.get(guild_id)
                if text_channel:
                    await text_channel.send(f"❌ File not found: {file_to_play}")
                return
        else:
            logger.info(f"Playing YouTube stream")

        # Create callback
        def after_playing(error):
            if error:
                logger.error(f"[FFmpeg Error] {error}")
            else:
                logger.info("Song finished playing")
            
            coro = self.play_next(guild_id)
            asyncio.run_coroutine_threadsafe(coro, self.bot.loop)

        try:
            # Check if voice client is still valid
            if not vc.is_connected():
                logger.error("Voice client disconnected before playing")
                return
            
            logger.info("Creating FFmpeg audio source")
            source = discord.FFmpegPCMAudio(file_to_play, **FFMPEG_OPTIONS)
            
            logger.info("Starting playback")
            vc.play(source, after=after_playing)
            
            logger.info("Playback started successfully")
            
        except discord.ClientException as e:
            logger.error(f"Discord client exception: {e}", exc_info=True)
            text_channel = self.text_channels.get(guild_id)
            if text_channel:
                await text_channel.send(f"❌ Already playing audio or voice client error")
            return
        except Exception as e:
            logger.error(f"Playback exception: {e}", exc_info=True)
            text_channel = self.text_channels.get(guild_id)
            if text_channel:
                try:
                    await text_channel.send(f"❌ Failed to play audio: {e}")
                except:
                    pass
            return

        # Send now playing message
        text_channel = self.text_channels.get(guild_id)
        if text_channel:
            try:
                embed = discord.Embed(
                    title="Now Playing" if title.endswith((".mp4", ".mp3")) else "Now Playing (YouTube)",
                    description=title if title.endswith((".mp4", ".mp3")) else f"[{title}]({page_url})",
                    color=discord.Color.red()
                )
                await text_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Failed to send now playing message: {e}")

    async def add_to_queue(self, interaction: discord.Interaction, query: str):
        """Add a song to the queue"""
        guild_id = interaction.guild.id

        # Handle local file directly
        local_file = os.path.abspath(query) if os.path.isfile(query) else None
        if local_file:
            logger.info(f"Adding local file to queue: {local_file}")
            self.music_queues.setdefault(guild_id, []).append((os.path.basename(local_file), local_file, 'local file'))
            return os.path.basename(local_file), 'local file'

        # Handle YouTube
        try:
            logger.info(f"Searching YouTube for: {query}")
            
            with YoutubeDL(YDL_OPTIONS) as ydl:
                search_query = query if query.startswith("http") else f"ytsearch:{query}"
                info = ydl.extract_info(search_query, download=False)
                
                if "entries" in info:
                    info = info["entries"][0]
                
                url = info.get("url")
                title = info.get("title", "Unknown")
                page_url = info.get("webpage_url", query)
                
                logger.info(f"Found: {title}")

            if not url:
                logger.error("Could not extract URL from YouTube")
                await interaction.followup.send("Could not get a playable URL from YouTube.")
                return None, None

            self.music_queues.setdefault(guild_id, []).append((title, url, page_url))
            return title, page_url
            
        except Exception as e:
            logger.error(f"Error extracting YouTube info: {e}", exc_info=True)
            await interaction.followup.send(f"Error processing YouTube query: {str(e)[:100]}")
            return None, None

    @app_commands.command(name="playyt", description="Play a YouTube or local song.")
    async def playyt(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        logger.info(f"playyt command called by {interaction.user} with query: {query}")

        if not interaction.user.voice:
            await interaction.followup.send("You're not in a voice channel.", ephemeral=True)
            return

        guild_id = interaction.guild.id
        self.text_channels[guild_id] = interaction.channel

        title, page_url = await self.add_to_queue(interaction, query)
        if not title:
            return

        vc = interaction.guild.voice_client
        
        # If not connected, the user should use the join command from the other cog first
        if not vc or not vc.is_connected():
            await interaction.followup.send("❌ Bot is not in a voice channel. Use the join command first!")
            return

        # Start playing if nothing is currently playing
        if not vc.is_playing() and not vc.is_paused():
            logger.info("Starting playback immediately")
            await self.play_next(guild_id)
        else:
            logger.info("Added to queue")
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Added to Queue",
                    description=title if title.endswith((".mp4", ".mp3")) else f"[{title}]({page_url})",
                    color=discord.Color.blue()
                )
            )

    @app_commands.command(name="queue", description="View the current music queue.")
    async def queue(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        queue = self.music_queues.get(guild_id, [])
        
        currently_playing = self.currently_playing.get(guild_id)
        
        if not queue and not currently_playing:
            await interaction.response.send_message("The queue is empty.")
            return

        description = ""
        
        if currently_playing:
            title, _, page_url = currently_playing
            description += "**Now Playing:**\n"
            description += f"🎵 {title}\n\n" if title.endswith((".mp4", ".mp3")) else f"🎵 [{title}]({page_url})\n\n"
        
        if queue:
            description += "**Up Next:**\n"
            description += "\n".join([
                f"{i+1}. {t}" if t.endswith((".mp4", ".mp3")) else f"{i+1}. [{t}]({u})"
                for i, (t, _, u) in enumerate(queue[:10])
            ])
        
        embed = discord.Embed(title="🎶 Current Queue", description=description, color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="skip", description="Skip the current song.")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message("Nothing is currently playing.")
            return

        logger.info(f"Skipping song in guild {interaction.guild.id}")
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
    logger.info(f"YouTube cog loaded - Version {cog.version}")
    
    embed = discord.Embed(
        title=f'YT Cog Successfully loaded',
        description=f'Version: {cog.version}\nCommands: {len(cog.get_app_commands())}'
    )
    update = bot.get_channel(1428731822442811403)
    if update:
        await update.send(embed=embed)