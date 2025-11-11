import os
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
import datetime
import logging
import json
import aiofiles
import datetime

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
commandlog = logging.FileHandler(filename='commands.log', encoding='utf-8', mode='w')

formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
handler.setFormatter(formatter)
commandlog.setFormatter(formatter)

console = logging.StreamHandler()
logger.addHandler(handler)
logger.addHandler(console)

load_dotenv()

TOKEN = os.getenv("TOKEN")
SERVER_ID = 1427325336831660245  # replace with your actual guild ID
SETTINGS_FILE = "guild_settings.json"

DEFAULT_SETTINGS = {
    "prefix": "!",
    "language": "en",
    "logging": True,
    "modchannel": None,
    "welcome_channel": None
}


async def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        async with aiofiles.open(SETTINGS_FILE, "w") as f:
            await f.write(json.dumps({}, indent=4))
        return {}

    async with aiofiles.open(SETTINGS_FILE, "r") as f:
        data = await f.read()
        return json.loads(data) if data else {}


async def save_settings(settings: dict):
    async with aiofiles.open(SETTINGS_FILE, "w") as f:
        await f.write(json.dumps(settings, indent=4))


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self.settings = {}

    async def setup_hook(self):
        # Load all cogs
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                await self.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: {filename}")
        
        await self.tree.sync()
        print(f"Slash commands synced to guild {SERVER_ID}.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Connected to {len(self.guilds)} guild(s).")
        print("Bot is ready.")

        self.settings = await load_settings()

        update_channel = self.get_guild(SERVER_ID).get_channel(1428731822442811403)
        cog_info = []

        for name, cog in self.cogs.items():
            version = getattr(cog, "version", "unknown")
            cog_info.append(f"**{name}** — v{version} including commands:")
            for idx, command in enumerate(cog.get_app_commands()):
                cog_info.append(f"{idx}. */{command.name}*")

        embed = discord.Embed(
            title="Bot Online!",
            description="**__Cogs loaded:__**\n" + "\n".join(cog_info),
            color=discord.Color.green()
        )
        if datetime.datetime.now().month == 11 and datetime.datetime.now().day == 10:
            jasmineEmbed = discord.Embed(title='are you an todays date', description='because you are an 11 out of 10', color=discord.Color.purple())
            jasmineEmbed.set_footer(text='sorry...')
            jasmine = discord.getUser(1268762365566910619)
            jasmine.send(embed=jasmineEmbed)
            print('message sent vro why did u do this :wilted-rose:')


        await update_channel.send(embed=embed)

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Load current settings if not already loaded
        if not self.settings:
            self.settings = await load_settings()

        guild_id = str(message.guild.id)
        if guild_id not in self.settings:
            self.settings[guild_id] = DEFAULT_SETTINGS.copy()
            print(f"Created default settings for guild {guild_id}")
            await save_settings(self.settings)

        await self.process_commands(message)

    async def on_app_command_completion(self, interaction, command):
        msg = f"Slash command run: /{command.name} by {interaction.user} in #{interaction.channel}"
        print(msg)
        logging.getLogger('command').info(msg)

    async def on_command(self, ctx):
        msg = f"Prefix command run: {ctx.command} by {ctx.author} in #{ctx.channel}"
        print(msg)
        logging.getLogger('command').info(msg)
                                     

async def main():
    bot = MyBot()
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
