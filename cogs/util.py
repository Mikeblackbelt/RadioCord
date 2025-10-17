import discord
from discord.ext import commands
from discord import app_commands
from discord import FFmpegPCMAudio
import os

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = '1.0'

    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping(self, interaction: discord.Interaction):
        latency = self.bot.latency * 1000
        embed = discord.Embed(title="🏓 Pong!", description=f"Latency: {latency:.2f}ms", color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="join", description="Join your voice channel.")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("You’re not in a voice channel.", ephemeral=True)
            return
        channel = interaction.user.voice.channel
        await channel.connect()
        await interaction.response.send_message(f"Joined `{channel.name}`.")

    @app_commands.command(name="leave", description="Leave the current voice channel.")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message("I’m not in a voice channel.", ephemeral=True)
            return
        await vc.disconnect()
        await interaction.response.send_message("Disconnected from the voice channel.")

    @app_commands.command(name="stop", description="Stop the current playback.")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message("No audio is playing.", ephemeral=True)
            return
        vc.stop()
        await interaction.response.send_message("Playback stopped.")


async def setup(bot):
    cog = Utils(bot)
    await bot.add_cog(cog)
    embed = discord.Embed(title=f'Utility cog Successfully loaded', description=f'Version: {cog.version}\nCommands: {cog.get_app_commands()}')
    update = bot.get_channel(1428731822442811403)
    if update:
        await update.send(embed=embed)