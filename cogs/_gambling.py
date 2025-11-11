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
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

class blackjackView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.player_hand = []
        self.dealer_hand = []
        self.game_over = False

    async def on_timeout(self, interaction: discord.Interaction):
        if not self.game_over:
            await interaction.response.send_message("Game timed out!")
            self.stop()

        

class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = '1.0'
    
    @app_commands.command(name='blackjack', description='Play a game of blackjack')
