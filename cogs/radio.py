import discord
from discord.ext import commands
from discord import app_commands
from pyradios import RadioBrowser
from discord import FFmpegPCMAudio
import asyncio

class Radio(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="playradio", description="Play a radio station by name.")
    async def playradio(self, interaction: discord.Interaction, station_name: str):
        await interaction.response.defer()
        try:
            if not interaction.user.voice:
                await interaction.followup.send("You’re not in a voice channel.", ephemeral=True)
                return

            rb = RadioBrowser()
            results = rb.search(name=station_name, name_exact=False, limit=1)
            if not results:
                await interaction.followup.send("No station found.", ephemeral=True)
                return

            station = results[0]
            stream_url = station["url"]
            channel = interaction.user.voice.channel

            vc = interaction.guild.voice_client
            if not vc:
                vc = await channel.connect()
                await interaction.followup.send(f"Joined `{channel.name}`...")
            elif vc.channel != channel:
                await vc.move_to(channel)
                await interaction.followup.send(f"Joined `{channel.name}`...")

            if vc.is_playing():
                vc.stop()

            vc.play(FFmpegPCMAudio(stream_url))
            embed = discord.Embed(title="Now Playing", description=f"🎶 {station['name']}", color=discord.Color.green())
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Radio(bot))
