import discord
from discord.ext import commands
from discord import app_commands
from yt_dlp import YoutubeDL


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

    @app_commands.command(name="playyt", description="Play audio from YouTube by search or URL.")
    @app_commands.describe(query="Search term or YouTube URL")
    async def playyt(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            await interaction.followup.send("You’re not in a voice channel.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        if not vc:
            vc = await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)

        if vc.is_playing():
            vc.stop()

        try:
            with YoutubeDL(YDL_OPTIONS) as ydl:
                search_query = query if query.startswith("http") else f"ytsearch:{query}"
    
                info = ydl.extract_info(search_query, download=False)
                if "entries" in info:
                    info = info["entries"][0]
                url = info["url"]
                title = info.get("title", "Unknown")
                page_url = info.get("webpage_url", query)

            vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS),
                    after=lambda e: print(f"Playback ended: {e}" if e else "Playback finished"))

            embed = discord.Embed(
                title="Now Playing (YouTube)",
                description=f"[{title}]({page_url})",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(title="Error", description=f"Could not play the requested audio.\nPlease Report this Error: {str(e)}", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(YouTube(bot))
