import discord
from discord.ext import commands
from discord import app_commands
import _encrypt
import json

SETTINGS_FILE = "cogs/commands.json"  # your master JSON

DEFAULT_USER_SETTINGS = {
    'message-deletion-tracking': True,
    'shippable': True,
    'language': 'en',
    'recieve-unprompted-dms': True
}



class HelpPaginator(discord.ui.View):
    def __init__(self, pages):
        super().__init__(timeout=120)
        self.pages = pages
        self.current = 0

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = (self.current - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = (self.current + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = '1.0'
        with open(SETTINGS_FILE, "r") as f:
            self.commands_master = json.load(f)

    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping(self, interaction: discord.Interaction):
        latency = self.bot.latency * 1000
        embed = discord.Embed(title="🏓 Pong!", description=f"Latency: {latency:.2f}ms", color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="join", description="Join your voice channel.")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("You’re not in a voice channel.", ephemeral=True)
            return
        channel = interaction.user.voice.channel
        await channel.connect()
        await interaction.response.send_message(f"Joined `{channel.name}`.")

    @app_commands.command(name="leave", description="Leave the current voice channel.")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message("I’m not in a voice channel.", ephemeral=True)
            return
        await vc.disconnect()
        await interaction.response.send_message("Disconnected from the voice channel.")

    @app_commands.command(name="stop", description="Stop the current playback.")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            await interaction.response.send_message("No audio is playing.", ephemeral=True)
            return
        vc.stop()
        await interaction.response.send_message("Playback stopped.")

    @app_commands.command(name='export_data', description='Export all your data (this will NOT clear it).')
    async def export(self, interaction: discord.Interaction):
        user = interaction.user

        with open("cogs/_journals_.json", "r") as f:
            journals = json.load(f)

        if str(user.id) not in journals:
            data = ''
        else:
            data = '**__(Encrypted)__**:\n\n\n' + str(journals[str(user.id)] if str(user.id) in journals else 'Journal Data not found') 

        with open('cogs/_context_.json', 'r') as f:
            context = json.load(f)
        
        data += '\n\n**__context__**\n\n' + str(context[str(user.id)] if str(user.id) in context else '')
        while len(data) > 0:
            await user.send(data[:2000])
            data = data[2000:]

        await interaction.response.send_message('Sent! Check DMs.', ephemeral=True)

    @app_commands.command(name='decrypt', description='Decrypt Data from the bot.')
    @app_commands.describe(data='Data to Decrypt')
    async def decrypt(self, interaction: discord.Interaction, data: str):
        decrypted = _encrypt.decrypt(data)
        embed = discord.Embed(
            title='Decrypted Data',
            description=f'{data} → {decrypted}',
            color=discord.Color.blurple()
        )
        await interaction.user.send(embed=embed)
        await interaction.response.send_message("Check DMs!", ephemeral=True)

    @app_commands.command(name='help', description='Show all bot commands.')
    async def help_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        per_page = 10
        pages = []

        commands_sorted = sorted(self.commands_master.items(), key=lambda x: x[1].get("Category", ""))
        
        for i in range(0, len(commands_sorted), per_page):
            chunk = commands_sorted[i:i+per_page]
            embed = discord.Embed(
                title=f'Bot Commands (Page {i//per_page + 1})',
                color=discord.Color.blurple()
            )
            for name, data in chunk:
                desc = f"{data.get('Description','No description')}\nCategory: {data.get('Category','None')}\nState: {data.get('State','Unknown')}\nPermissions: {data.get('Permissions','None')}"
                embed.add_field(name=f"/{name}", value=desc[:1024], inline=False)
            embed.set_footer(text=f'Page {i//per_page + 1}/{(len(commands_sorted)-1)//per_page + 1}')
            pages.append(embed)

        if not pages:
            await interaction.followup.send("No commands found.", ephemeral=False)
            return

        if len(pages) == 1:
            await interaction.followup.send(embed=pages[0], ephemeral=False)
        else:
            view = HelpPaginator(pages)
            await interaction.followup.send(embed=pages[0], view=view, ephemeral=False)
    
    @app_commands.command(name='user-settings', description='edit user settings')
    async def usersettings(self, interaction: discord.Interaction):
        return #not finish


async def setup(bot):
    cog = Utils(bot)
    await bot.add_cog(cog)
    embed = discord.Embed(
        title=f'Utility cog successfully loaded',
        description=f'Version: {cog.version}\nCommands loaded: {len(cog.commands_master)}'
    )
    update = bot.get_channel(1428731822442811403)
    if update:
        await update.send(embed=embed)
