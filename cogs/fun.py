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
from PIL import Image, ImageDraw
import io

class gs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = '1.0'

    def make_circle(self, im: Image.Image, size: int):
        im = im.resize((size, size))
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        result = Image.new("RGBA", (size, size))
        result.paste(im, (0, 0), mask)
        return result

    @app_commands.command(name='messages', description='Get Guild Top Messages Stats')
    async def stats(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        guild = interaction.guild
        senders = Counter()

        for channel in guild.text_channels:
            try:
                async for message in channel.history(limit=None):
                    if not message.author.bot:
                        senders[message.author] += 1
            except discord.Forbidden:
                continue

        top_senders = senders.most_common(10)

        embed = discord.Embed(
            title=f"Top Message Senders in {guild.name}",
            color=discord.Color.blurple()
        )

        if not top_senders:
            embed.description = "No messages found. Your server is quieter than a library on Mars."
        else:
            for i, (user, count) in enumerate(top_senders, start=1):
                embed.add_field(name=f"#{i} {user.display_name}", value=f"{count} messages", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name='ship', description='ship two users because you are weird')
    @app_commands.describe(user1='user 1', user2='user2')
    async def ship(self, interaction: discord.Interaction, user1: discord.User, user2: discord.User):
        await interaction.response.defer()

        url1 = user1.avatar.url or user1.default_avatar.url
        url2 = user2.avatar.url or user2.default_avatar.url

        async with aiohttp.ClientSession() as session:
            async with session.get(url1) as r1, session.get(url2) as r2:
                avatar1 = Image.open(io.BytesIO(await r1.read())).convert("RGBA")
                avatar2 = Image.open(io.BytesIO(await r2.read())).convert("RGBA")
        
        heart = Image.open('_heart.png')
        height = 256
        avatar1 = self.make_circle(avatar1, height)
        avatar2 = self.make_circle(avatar2, height)

        heart = heart.resize((height, height))

        total_width = (2*avatar1.width//3 + 2*heart.width//3 + avatar2.width)
        success = 1 + (user1.id + user2.id - 45) % 100
        result = Image.new("RGB", (total_width, height), (int(success*255),int(success*255),int(success*255)))
        result.paste(avatar1, (0, 0), avatar1)
        result.paste(avatar2, (2*avatar1.width//3 + 2*heart.width//3, 0), avatar2)
        result.paste(heart, (2*avatar1.width//3, 0), heart)


        # Save to in-memory buffer
        buf = io.BytesIO()
        result.save(buf, format="PNG")
        buf.seek(0)

        # Create discord File
        file = discord.File(buf, filename="love.png")

        embed = discord.Embed(
            title=f'Your ship: {user1.name[:len(user1.name)//2]}{user2.name[len(user2.name)//2:]}',
            description=f'Chance of Success: {success}%'
        )
        embed.set_image(url="attachment://love.png")

        # Send embed with file
        await interaction.followup.send(embed=embed, file=file)



async def setup(bot):
    await bot.add_cog(gs(bot))