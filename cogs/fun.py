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
        with open('cogs\\battle.txt','r') as f:
            self.bt = f.read().splitlines()
        with open('cogs\\battleend.txt', 'r') as f:
            self.be = f.read().splitlines()
        self.sf = {0: 'anything is possible, except for this.', 6: 'anything is possible', 10: 'holy airball', 17: 'dont think about it too much', 24: 'could be worse, but not alot', 33: 'there may be a chance', 41: 'lowk not bad', 50: 'mayyybeee????', 57: 'would mkae a good fanfic', 63: 'i support', 67: 'mango mustard', 68: 'shoot your shot', 75: 'this is a free throw', 82: 'woah', 88: 'they look cute together', 94: 'soulmates ??? maybe ???', 100: 'just kiss already smh'}

    def make_circle(self, im: Image.Image, size: int):
        im = im.resize((size, size))
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        result = Image.new("RGBA", (size, size))
        result.paste(im, (0, 0), mask)
        return result

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

        flavor_text = ''
        for i in self.sf:
            if success >= i: flavor_text = self.sf[i]
            else: break

        embed = discord.Embed(
            title=f'Your ship: {user1.name[:len(user1.name)//2]}{user2.name[len(user2.name)//2:]}',
            description=f'Chance of Success: {success}%'
        )
        embed.set_image(url="attachment://love.png")
        embed.set_footer(text=f'{flavor_text} | try /{random.choice([command.name for command in self.get_app_commands()])}')

        # Send embed with file
        await interaction.followup.send(embed=embed, file=file)

    @app_commands.command(name='best_match', description='Find the best match in the server')
    @app_commands.describe(user1='A user, if any')
    async def bestMatch(self, interaction: discord.Interaction, user1: discord.User = None):
        await interaction.response.defer(thinking=True, ephemeral=False)
        await interaction.guild.chunk()

        guild = interaction.guild
        active_users = set()

        channels = [c for c in guild.text_channels if c.permissions_for(guild.me).read_messages][:15]

        async def fetch_recent_users(channel):
            users = set()
            try:
                async for msg in channel.history(limit=500, oldest_first=False):
                    if msg.author and not msg.author.bot:
                        member = guild.get_member(msg.author.id)
                        if member:
                            users.add(member)
                            #print(type(member))
            except:
                pass
            return users
        
        def mention_safe(u, guild):
            return u.mention if hasattr(u, "mention") and len(u.mention) < 25 else f"**{u.name}**"



        results = await asyncio.gather(*(fetch_recent_users(ch) for ch in channels))
        for users in results:
            active_users.update(users)

        members = list(active_users)
        random.shuffle(members)

        if len(members) < 2:
            await guild.chunk()
            members = interaction.guild.members
            await interaction.followup.send("Not enough active members found in the last messages. Using inactive members.", ephemeral=True)
            if interaction.user.id ==  928109349140824125: await interaction.followup.send(len(members), ephemeral=True)

        best_score = -1
        best_pair = None

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
            description=f'{mention_safe(user1, interaction.guild)} ❤️ {mention_safe(user2, interaction.guild)}\nChance of Success: {best_score}%',
        )
        flavor_text = ''
        for i in self.sf:
            if best_score >= i: flavor_text = self.sf[i]
            else: break
        embed.set_footer(text=f'{flavor_text} | try /{random.choice([command.name for command in self.get_app_commands()])}')

        embed.set_image(url="attachment://best_match.png")
        print(user1 in guild.members, user2 in guild.members)
        
        await interaction.followup.send(embed=embed, file=file, ephemeral=False)


    @app_commands.command(name='coin-flip', description='flip a coin')
    async def coin_flip(self, interaction: discord.Interaction):
        side = random.choice(['Heads', 'Tails'])
        if random.random() < 0.01:
            embed = discord.Embed(title='🪙 What?', description='It landed on...it\'s side?', color=discord.Color.dark_gold())
        else:
            embed = discord.Embed(title = f'🪙 {side}', description=f'It landed on {side}', color=discord.Color.yellow())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='roll-die', description='roll a n-sided dice')
    @app_commands.describe(n='the amount of sides')
    async def roll_die(self, interaction: discord.Interaction, n: int = 6):
        await interaction.response.defer()
        embed = discord.Embed(title='Rolling...', description=f'Rolling a d{n}...', color=discord.Color.dark_red())
        msg = await interaction.followup.send(embed=embed)
        await asyncio.sleep(2.67)
        embed = discord.Embed(title=f'You Rolled a {random.randint(1,n)}', description=f'good boy', color=discord.Color.from_rgb(127,210,121))
        await msg.edit(embed = embed)

    @app_commands.command(name='battle', description='we have love, now we have war')
    @app_commands.describe(user1='First user to fight', user2='Second user to fight')
    async def battle(self, interaction: discord.Interaction, user1: discord.User, user2: discord.User):
        await interaction.response.defer()
        battle_log = ''
        chance_end = 0.00

        embed = discord.Embed(
            title=f"⚔️ Battle: {user1.display_name} vs {user2.display_name}",
            description="**Battle Log:**",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )

        msg = await interaction.followup.send(embed=embed)

        while True:
            attacker = random.choice([user1, user2])
            target = user1 if attacker is not user1 else user2

            log_line = ""
            if random.random() < chance_end:
                log_line = random.choice(self.be).replace('{attacker}', attacker.display_name).replace('{target}', target.display_name)
                battle_log += f"`{log_line}`\n"

                # End embed
                color = discord.Color.green() if attacker == user1 else discord.Color.red()
                end_embed = discord.Embed(
                    title=f"⚔️ Battle: {attacker.display_name} DEFEATS {target.display_name}",
                    description="**Battle Log:**",
                    color=color,
                    timestamp=discord.utils.utcnow()
                )

                # Chunk the battle log
                chunks = [battle_log[i:i+950] for i in range(0, len(battle_log), 950)]
                for chunk in chunks[:25]:
                    end_embed.add_field(
                        name="\u200b",
                        value=f"```ansi\n{chunk}```",
                        inline=False
                    )

                await msg.edit(embed=end_embed)
                break

            else:
                log_line = random.choice(self.bt).replace('{attacker}', attacker.name).replace('{target}', target.name)
                battle_log += f"`{log_line}`\n"
                chance_end += 0.02

                update_embed = discord.Embed(
                    title=f"⚔️ Battle: {user1.display_name} vs {user2.display_name}",
                    description="**Battle Log:**",
                    color=discord.Color.blurple(),
                    timestamp=discord.utils.utcnow()
                )

                # Chunk log while still fighting
                chunks = [battle_log[i:i+950] for i in range(0, len(battle_log), 950)]
                for chunk in chunks[:25]:
                    update_embed.add_field(
                        name="\u200b",
                        value=f"```ansi\n{chunk}```",
                        inline=False
                    )

                update_embed.set_footer(text="now ship the users for enemies to lovers")
                await msg.edit(embed=update_embed)

                await asyncio.sleep(2)





async def setup(bot):
        await bot.add_cog(gs(bot))