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

    """@app_commands.command(name='messages', description='Get Guild Top Messages Stats')
    async def stats(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        guild = interaction.guild
        senders = Counter()

        for channel in guild.text_channels:
            try:
                async for message in channel.history(limit=1000):
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

        await interaction.followup.send(embed=embed)"""

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
        embed.set_footer(text='Looking for a match? Try /best_match!')

        # Send embed with file
        await interaction.followup.send(embed=embed, file=file)

    @app_commands.command(name='best_match', description='Find the best match in the server')
    @app_commands.describe(user1='A user, if any')
    async def bestMatch(self, interaction: discord.Interaction, user1: discord.User = None):
        await interaction.response.defer(thinking=True)
        guild = interaction.guild
        active_users = set()

        # limit number of channels to avoid rate-limits
        channels = [c for c in guild.text_channels if c.permissions_for(guild.me).read_messages][:15]

        async def fetch_recent_users(channel):
            users = set()
            try:
                async for msg in channel.history(limit=500, oldest_first=False):
                    if msg.author and not msg.author.bot:
                        users.add(msg.author)
            except (discord.Forbidden, discord.HTTPException):
                pass
            return users

        # Concurrently gather active users across channels
        results = await asyncio.gather(*(fetch_recent_users(ch) for ch in channels))
        for users in results:
            active_users.update(users)

        members = list(active_users)
        random.shuffle(members)

        if len(members) < 2:
            await interaction.followup.send("Not enough active members found in the last messages.")
            return

        best_score = -1
        best_pair = None

        # Full O(n²) search — accurate but still tolerable for small/medium sets
        if not user1:
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    u1, u2 = members[i], members[j]
                    score = 1 + (u1.id + u2.id - 45) % 100
                    if score > best_score:
                        best_score, best_pair = score, (u1, u2)
        else:
            for u2 in members:
                score = 1 + (user1.id + u2.id - 45) % 100
                if score > best_score:
                    best_score, best_pair = score, (user1, u2)

        if not best_pair:
            await interaction.followup.send("Could not find a match.")
            return

        user1, user2 = best_pair
        url1 = user1.display_avatar.url
        url2 = user2.display_avatar.url

        # Concurrently fetch avatar images
        async with aiohttp.ClientSession() as session:
            async def fetch_image(url):
                async with session.get(url) as r:
                    return Image.open(io.BytesIO(await r.read())).convert("RGBA")
            avatar1, avatar2 = await asyncio.gather(fetch_image(url1), fetch_image(url2))

        heart = Image.open('_heart.png')
        height = 256
        avatar1 = self.make_circle(avatar1, height)
        avatar2 = self.make_circle(avatar2, height)
        heart = heart.resize((height, height))

        total_width = (2*avatar1.width//3 + 2*heart.width//3 + avatar2.width)
        gray = int(best_score * 255 / 100)
        result = Image.new("RGB", (total_width, height), (gray, gray, gray))
        result.paste(avatar1, (0, 0), avatar1)
        result.paste(avatar2, (2*avatar1.width//3 + 2*heart.width//3, 0), avatar2)
        result.paste(heart, (2*avatar1.width//3, 0), heart)


        buf = io.BytesIO()
        result.save(buf, format="PNG")
        buf.seek(0)
        file = discord.File(buf, filename="best_match.png")

        embed = discord.Embed(
            title=f'Best match: {user1.name[:len(user1.name)//2]}{user2.name[len(user2.name)//2:]}',
            description=f'<@{user1.id}> ❤️ <@{user2.id}>\nChance of Success: {best_score}%',
        )
        embed.set_image(url="attachment://best_match.png")
        await interaction.followup.send(embed=embed, file=file)


    @app_commands.command(name='coin-flip', description='flip a coin')
    async def coin_flip(self, interaction: discord.Interaction):
        side = random.choice(['Heads', 'Tails'])
        if random.random() < 0.01:
            embed = discord.Embed(title='🪙 What?', description='It landed on...it\'s side?')
        else:
            embed = discord.Embed(title = f'🪙 {side}', description=f'It landed on {side}')
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='roll-die', description='roll a n-sided dice')
    @app_commands.describe(n='the amount of sides')
    async def roll_die(self, interaction: discord.Interaction, n: int = 6):
        await interaction.response.defer()
        embed = discord.Embed(title='Rolling...', description=f'Rolling a d{n}...')
        msg = await interaction.followup.send(embed=embed)
        await asyncio.sleep(2.67)
        embed = discord.Embed(title=f'You Rolled a {random.randint(1,n)}', description=f'good boy')
        await msg.edit(embed = embed)
        







async def setup(bot):
    await bot.add_cog(gs(bot))