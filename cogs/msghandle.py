import discord
from discord.ext import commands
from discord import app_commands
import os
import aiohttp
from datetime import datetime
import dotenv
from collections import Counter
import _encrypt as encrypt
import json
import random
from PIL import Image, ImageDraw
import io
import asyncio

class message_handler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = '1.0'

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.content == 'ping_message_handler':
            await message.channel.send('message handler active')
    
    #@commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        # Prevent responding to your own ghost
        if message.author == self.bot.user:
            return

        channel = message.channel
        content = message.content or "[no text content]"
        author = message.author

        await channel.send(f"{author.mention} deleted a message: {content}")

    #@app_commands.command(name='prev5',description='testing')
    async def prev5(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async for messages in interaction.channel.history(limit=5):
            await interaction.followup.send(messages.content) #poiutrewqazXCVBGHJUI0[-=\,,,,,,,,,,,KKKKKK;KL;L;L;L;L;L;L;L; I HATE YIUR COMPURER MATTIYLCHFDEGFBFHGJUGYFGHYCFGJNFGHTYRFGXFBXTGDFXGTDXFGRTDFGRTDFHGTFGHTHFGFRTDHBUTYFDGHBTUYFHUTYFGHYTDFGRYDTHDBYFGXHBCFYGHBYFDTFGVTYFGFHGBYFTRYDHTDG

        
async def setup(bot):
    await bot.add_cog(message_handler(bot))