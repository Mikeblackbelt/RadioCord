import os
import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from discord import FFmpegPCMAudio
import aiohttp
import nacl
from pyradios import RadioBrowser
import ffmpeg

load_dotenv()

RADIO_API = "https://us1.api.radio-browser.info/json/stations/search"

SERVER_ID = '1427325336831660245'

class MyBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix="!", intents=intents)
    
    async def setup_hook(self):
        # Sync commands once at startup
        guild = discord.Object(id=SERVER_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync()
        print("Slash commands synced.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Guilds: {self.guilds}")
        print("Bot is ready.")

intents = discord.Intents.default()
intents.message_content = True
bot = MyBot(intents=intents)


@bot.tree.command(name="ping", description="Check bot latency.")
async def ping(interaction: discord.Interaction):
    try:
        embed = discord.Embed(title="Pong 🏓", description=f"Latency: {bot.latency * 1000:.2f} ms", color=discord.Color.blurple())
    except Exception as e:
        embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='join', description='Join the voice channel you are in.')
async def join(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        await channel.connect()
        embed = discord.Embed(title="Joined Voice Channel", description=f"Joined {channel.name}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="You are not in a voice channel.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name='leave', description='Leave the voice channel.')
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        embed = discord.Embed(title="Left Voice Channel", description="Disconnected from the voice channel.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="Error", description="I am not in a voice channel.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name='play', description='Play a radio station by name.')
@app_commands.describe(station_name="Name of the radio station to play")
async def play(interaction: discord.Interaction, station_name: str):
    await interaction.response.defer()
    try:
        if not interaction.user.voice:
            embed = discord.Embed(title="Uh Oh!", description="You are not in a voice channel.", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return


        for i in range(10):  # Retry up to 10 times
            mirrors = ['us1', 'de1', 'nl1', 'fr1', 'uk1']
            rb = RadioBrowser(mirror=mirrors[i % len(mirrors)])
            try: results = rb.search(name=station_name, name_exact=False, limit=1)
            except Exception as e:
                if i == 9:
                    raise e
                
                await interaction.followup.send(f"Retrying... ({i+1}/10)", ephemeral=True)
                await asyncio.sleep(1)
                continue
            

        if not results:
            embed = discord.Embed(title="Station Not Found", description=f"No station found for '{station_name}'.", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        station = results[0]
        stream_url = station["url"]
        channel = interaction.user.voice.channel

        # Connect or move bot to the voice channel
        if not interaction.guild.voice_client:
            vc = await channel.connect()
        else:
            vc = interaction.guild.voice_client
            if vc.channel != channel:
                await vc.move_to(channel)

        if vc.is_playing():
            vc.stop()

        # Play the stream
        vc.play(FFmpegPCMAudio(stream_url), after=lambda e: print(f"Stream ended or error: {e}" if e else "Stream stopped"))
        embed = discord.Embed(title="Now Playing", description=f"Streaming **{station['name']}**", color=discord.Color.green())
        await interaction.followup.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(title="Error", description=f"An error occurred: {str(e)}", color=discord.Color.red())
        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name='stop', description='Stop playing and clear the queue.')
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        embed = discord.Embed(title="Stopped", description="Playback has been stopped.", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(title="What?", description="No audio is playing.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
TOKEN = os.getenv("TOKEN")

if __name__ == "__main__":
    bot.run(TOKEN)