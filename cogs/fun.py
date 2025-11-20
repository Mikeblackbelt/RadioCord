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


class gs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = '1.0'
        with open('cogs\\battle.txt','r') as f:
            self.bt = f.read().splitlines()
        with open('cogs\\battleend.txt', 'r') as f:
            self.be = f.read().splitlines()
        self.sf = {0: 'anything is possible, except for this.', 6: 'anything is possible', 10: 'holy airball', 17: 'dont think about it too much', 24: 'could be worse, but not alot', 33: 'there may be a chance', 41: 'lowk not bad', 50: 'mayyybeee????', 57: 'would mkae a good fanfic', 63: 'i support', 67: 'mango mustard', 68: 'shoot your shot', 75: 'this is a free throw', 82: 'woah', 88: 'they look cute together', 94: 'soulmates ??? maybe ???', 99.4: 'just kiss already smh', 100: '<3 perfect match <3'}
        self.defaultMatches = [[708384424537882716,749326115939680288]]
    def make_circle(self, im: Image.Image, size: int):
        im = im.resize((size, size))
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        result = Image.new("RGBA", (size, size))
        result.paste(im, (0, 0), mask)
        return result

    def calc_success(self, uid1: int, uid2: int) -> int:
        if sorted([uid1, uid2]) == sorted([1268762365566910619, 928109349140824125]):
            return 100.00 
        elif sorted([uid1, uid2]) in [sorted(match) for match in self.defaultMatches]:
            return 99.999
        if uid2 > uid1:
            uid1, uid2 = uid2, uid1
        if uid1 == uid2:
            return (uid1 % 10000) / 100
        return round(((uid1 * 67 ^ uid2 * 67) % 10000) / 100, 2)

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
        success = self.calc_success(user1.id, user2.id)
        result = Image.new("RGB", (total_width, height), (int(success*2.55),int(success*2.55),int(success*2.55)))
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

        if success == 100 and 928109349140824125 not in [user1.id, user2.id]:
            success = 99.9999 #ONLY I CAN AHIEVE PERFECTION
        embed = discord.Embed(
            title=f'Your ship: {user1.name[:len(user1.name)//2]}{user2.name[len(user2.name)//2:]}',
            description=f'Chance of Success: {success}%',
            color= discord.Color.from_rgb(int(255 - success*2.55),int(success*2.55),50)
        )
        embed.set_image(url="attachment://love.png")
        embed.set_footer(text=f'{flavor_text} | try /{random.choice([command.name for command in self.get_app_commands()])}')

        # Send embed with file
        await interaction.followup.send(embed=embed, file=file)

    @app_commands.command(name='best_match', description='Find the best match in the server')
    @app_commands.describe(user1='A user, if any', returnall='Return all matches instead of the best one')
    async def bestMatch(self, interaction: discord.Interaction, user1: discord.User = None, returnall: bool = False):
        await interaction.response.defer(thinking=True, ephemeral=False)
        logger.info(f"/best_match invoked by {interaction.user} (user1={user1}, returnall={returnall})")

        if not (interaction.guild.chunked):
            await interaction.guild.chunk(cache=True)
            logger.info("Guild members chunked.")

        guild = interaction.guild
        active_users = set()
        channels = [c for c in guild.text_channels if c.permissions_for(guild.me).read_messages][:15]
        logger.info(f"Scanning {len(channels)} channels for recent users...")

        async def fetch_recent_users(channel):
            users = set()
            try:
                async for msg in channel.history(limit=500, oldest_first=False):
                    if msg.author and not msg.author.bot:
                        member = guild.get_member(msg.author.id)
                        if member:
                            users.add(member)
            except Exception as e:
                logger.warning(f"Error fetching users from {channel}: {e}")
            return users

        def mention_safe(u, guild):
            return u.mention if hasattr(u, "mention") and len(u.mention) < 25 else f"**{u.name}**"

        results = await asyncio.gather(*(fetch_recent_users(ch) for ch in channels))
        for users in results:
            active_users.update(users)

        logger.info(f"Found {len(active_users)} active users.")

        members = list(active_users)
        random.shuffle(members)

        if len(members) < 2:
            await guild.chunk()
            members = interaction.guild.members
            logger.warning("Not enough active members; using full member list.")
            await interaction.followup.send("Not enough active members found in the last messages. Using inactive members.", ephemeral=True)

        pairs = []
        if not user1:
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    u1, u2 = members[i], members[j]
                    score = self.calc_success(u1.id, u2.id) 
                    pairs.append((score, u1, u2))
        else:
            for u2 in members:
                if u2.id == user1.id:
                    continue
                score = self.calc_success(user1.id, u2.id)  
                pairs.append((score, user1, u2))

        logger.info(f"Generated {len(pairs)} pairs.")
        if (interaction.user.id == 928109349140824125 and False): #edit and True for debug 
            await interaction.user.send(f"Debug: {str(random.sample(pairs, k=len(pairs)))[:1000]}") # ignore
            await interaction.user.send(f"{min(pairs, key=lambda x: x[0])[0]}% - {max(pairs, key=lambda x: x[0])[0]}% scores among pairs.") # ignore
        
        if not pairs:
            await interaction.followup.send("No valid pairs found.", ephemeral=True)
            return

        pairs.sort(reverse=True, key=lambda x: x[0])
        logger.info(f"Top match score: {pairs[0][0]} between {pairs[0][1]} and {pairs[0][2]}")

        if returnall:
            embed = discord.Embed(title="All Matches", description="", color=discord.Color.random())
            top_pairs = pairs[:20]
            desc_lines = [f"{mention_safe(u1, guild)} ❤️ {mention_safe(u2, guild)} — **{score}%**" for score, u1, u2 in top_pairs]
            embed.description = "\n".join(desc_lines)
            await interaction.followup.send(embed=embed)
            return

        best_score, user1, user2 = pairs[0]
        url1 = user1.display_avatar.url
        url2 = user2.display_avatar.url
        logger.info(f"Downloading avatars for {user1} and {user2}")

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

        total_width = (2 * avatar1.width // 3 + 2 * heart.width // 3 + avatar2.width)
        gray = int(best_score * 255 / 100)
        result = Image.new("RGB", (total_width, height), (gray, gray, gray))
        result.paste(avatar1, (0, 0), avatar1)
        result.paste(avatar2, (2 * avatar1.width // 3 + 2 * heart.width // 3, 0), avatar2)
        result.paste(heart, (2 * avatar1.width // 3, 0), heart)

        buf = io.BytesIO()
        result.save(buf, format="PNG")
        buf.seek(0)
        file = discord.File(buf, filename="best_match.png")

        embed = discord.Embed(
            title=f'Best match: {user1.name[:len(user1.name)//2]}{user2.name[len(user2.name)//2:]}',
            description=f'{mention_safe(user1, guild)} ❤️ {mention_safe(user2, guild)}\nChance of Success: {best_score}%',
            color = discord.Color.from_rgb(int(255 - best_score*2.55),int(best_score*2.55),50)
        )

        flavor_text = ''
        for i in self.sf:
            if best_score >= i:
                flavor_text = self.sf[i]
            else:
                break

        embed.set_footer(text=f'{flavor_text} | try /{random.choice([command.name for command in self.get_app_commands()])}')
        embed.set_image(url="attachment://best_match.png")

        logger.info(f"Sending final embed for best match {user1} ❤️ {user2} ({best_score}%)")
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
    
    @app_commands.command(name='ship-concept', description='get a ship without expilicit users')
    @app_commands.describe(ship1='first half of the ship name', ship2='second half of the ship name')
    async def ship_concept(self, interaction: discord.Interaction, ship1: str, ship2: str):
        await interaction.response.defer()
        ship_name = ship1[:len(ship1)//2] + ship2[len(ship2)//2:]
        flavortext = ''

        if sorted([ship1, ship2]) == sorted(['mango', 'mustard']):
            success = 67.00
        elif sorted([ship1.lower(), ship2.lower()]) == sorted(['jasmine', 'michael']):
            success = 100.00
        else:
            hash1 = sum(41*67*ord(c) for c in ship1)
            hash2 = sum(41*67*ord(c) for c in ship2)
            success = round(((hash1 * 67 ^ hash2 * 67) % 10000) / 100, 2)
            for i in self.sf:
                if success >= i: flavortext = self.sf[i]
                else: break
        embed = discord.Embed(
            title=f'Your ship: {ship_name}',
            description=f'Chance of Success: {success}%',
            color = discord.Color.from_rgb(int(255 - success*2.55),int(success*2.55),50)
        )
        embed.set_footer(text=f'{flavortext} | try /{random.choice([command.name for command in self.get_app_commands()])}')
        await interaction.followup.send(embed=embed)

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

                color = discord.Color.green() if attacker == user1 else discord.Color.red()
                end_embed = discord.Embed(
                    title=f"⚔️ Battle: {attacker.display_name} DEFEATS {target.display_name}",
                    description="**Battle Log:**",
                    color=color,
                    timestamp=discord.utils.utcnow()
                )

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

    @app_commands.command(name='magic-8ball', description='Ask the magic 8ball a question')
    @app_commands.describe(question='Your question for the magic 8ball')
    async def magic_8ball(self, interaction: discord.Interaction, question: str):
        responses = ["It is certain.", "It is decidedly so.","Without a doubt.", "Yes – definitely.",  "I would be sure",  'Probably Yes.',       "Maybe.",       'Welp. Who knows?',       'Im sorry.',       "Don't count on it",       'My sources say no.',  "Very doubtful.","FUCK no",          "No", 'ask me in 6 or 7 minutes', 'what']
        flavortext = ["mysterious wisdom", "infinite knowledge", "cosmic insight", "knowledge of all that occurs", 'divine knowledge', 'ancient power', 'uhh..., ummm sfdsfhdkjh.... smartness']
        choice = random.randint(0, len(responses) - 1)
        if choice < 6: color = discord.Color.green()
        elif choice in [6, 7, 14,15]: color=discord.Color.yellow()
        else: color = discord.Color.red()
        embed = discord.Embed(color=color, title='The Magic 8ball says...', description=f'You asked: "**{question + "?" if "?" not in question else question}**".\nThe magic 8ball, in its *{random.choice(flavortext)}* says... **{responses[choice]}**')
        await interaction.response.send_message(embed=embed)   

async def setup(bot):
        await bot.add_cog(gs(bot))