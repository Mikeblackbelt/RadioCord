import os
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
import datetime
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
commandlog = logging.FileHandler(filename='commands.log', encoding='utf-8',mode='w' )

formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
handler.setFormatter(formatter)
commandlog.setFormatter(formatter)

console = logging.StreamHandler()
logger.addHandler(handler)
logger.addHandler(console)

load_dotenv()

TOKEN = os.getenv("TOKEN")
SERVER_ID = 1427325336831660245  # replace with your actual guild ID

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                await self.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: {filename} ")
        
        await self.tree.sync()
        print(f"Slash commands synced to guild {SERVER_ID}.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Connected to {len(self.guilds)} guild(s).")
        print("Bot is ready.")

        cog_info = []
        update_channel = self.get_guild(SERVER_ID).get_channel(1428731822442811403)
        for name, cog in self.cogs.items():
                version = getattr(cog, "version", "unknown")  # fallback if not defined
                cog_info.append(f"**{name}** — v{version} including commands:")
                for idx, command in enumerate(cog.get_app_commands()):
                    cog_info.append(f"{idx}. */{command.name}*")
                

        embed = discord.Embed(
                title="Bot Online!",
                description="**__Cogs loaded:__**\n" + "\n".join(cog_info),
                color=discord.Color.green()
        )

        await update_channel.send(embed=embed)
    
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
