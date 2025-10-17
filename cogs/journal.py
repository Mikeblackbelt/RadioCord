import discord
from discord.ext import commands
from discord import app_commands
import os
from datetime import datetime
import dotenv
import _encrypt as encrypt
import json

dotenv.load_dotenv()
class Journal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = '1.0'

    def load_journal(self, user_id):
        if not os.path.exists("cogs/_journals_.json"):
            return []
        with open("cogs/_journals_.json", "r") as f:
            journals = json.load(f)
        return journals.get(user_id, [])
    
    @app_commands.command(name='create_entry', description='Create a new journal entry for today.')
    @app_commands.describe(content='Content of your journal entry')
    async def create_entry(self, interaction: discord.Interaction, content: str):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        journals = {}
        if os.path.exists("cogs/_journals_.json"):
            with open("cogs/_journals_.json", "r") as f:
                journals = json.load(f)
        if user_id not in journals:
            journals[user_id] = {"last_journal": "", "entries": {}}
        today = datetime.now().strftime("%Y-%m-%d")
        if journals[user_id]["last_journal"] == today:
            await interaction.followup.send("You have already created a journal entry for today.", ephemeral=True)
            return
        encrypted_content = encrypt.encrypt(content)
        journals[user_id]["entries"][today] = encrypted_content
        journals[user_id]["last_journal"] = today
        with open("cogs/_journals_.json", "w") as f:
            json.dump(journals, f, indent=4)
        await interaction.followup.send("Journal entry created for today.", ephemeral=True)

    @app_commands.command(name='view_entry', description='View your journal entry for a specific date.')
    @app_commands.describe(date='Date of the journal entry (YYYY-MM-DD)')
    async def view_entry(self, interaction: discord.Interaction, date: str):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        if not os.path.exists("cogs/_journals_.json"):
            await interaction.followup.send("No journal entries found.", ephemeral=True)
            return
        with open("cogs/_journals_.json", "r") as f:
            journals = json.load(f)
        if user_id not in journals or date not in journals[user_id]["entries"]:
            await interaction.followup.send("No journal entry found for that date.", ephemeral=True)
            return
        encrypted_content = journals[user_id]["entries"][date]
        decrypted_content = encrypt.decrypt(encrypted_content)
        embed = discord.Embed(title=f"Journal Entry for {date}", description=decrypted_content, color=discord.Color.purple())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='list_entries', description='List all your journal entry dates.')
    async def list_entries(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = str(interaction.user.id)
        if not os.path.exists("cogs/_journals_.json"):
            await interaction.followup.send("No journal entries found.", ephemeral=True)
            return
        with open("cogs/_journals_.json", "r") as f:
            journals = json.load(f)
        if user_id not in journals or not journals[user_id]["entries"]:
            await interaction.followup.send("No journal entries found.", ephemeral=True)
            return
        entry_dates = list(journals[user_id]["entries"].keys())
        entry_dates.sort(reverse=True)
        for i in entry_dates:
            journal_entry = journals[user_id]["entries"][i]
            decrypted_content = encrypt.decrypt(journal_entry)
            if len(decrypted_content) > 100:
                entry_dates[entry_dates.index(i)] = f"{i}: {decrypted_content[:100]}..."
            else:
                entry_dates[entry_dates.index(i)] = f"{i}: {decrypted_content}"
        
        embed = discord.Embed(title="Your Journal Entries", description="\n".join(entry_dates), color=discord.Color.orange())
    
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    cog = Journal(bot)
    await bot.add_cog(cog)
    embed = discord.Embed(title=f'Journal Cog Successfully loaded', description=f'Version: {cog.version}\nCommands: {cog.get_app_commands()}')
    update = bot.get_channel(1428731822442811403)
    if update:
        await update.send(embed=embed)