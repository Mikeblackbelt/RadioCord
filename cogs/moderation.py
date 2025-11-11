import discord
from discord import app_commands
from discord.ext import commands
import aiofiles
import json
import os

SETTINGS_FILE = "guild_settings.json"

DEFAULT_SETTINGS = {
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


class SettingsModal(discord.ui.Modal, title="Edit Guild Setting"):
    def __init__(self, setting_name: str, current_value: str, guild_id: int):
        super().__init__()
        self.setting_name = setting_name
        self.guild_id = guild_id

        self.value_input = discord.ui.TextInput(
            label=f"New value for {setting_name}",
            default=str(current_value),
            required=True
        )
        self.add_item(self.value_input)

    async def on_submit(self, interaction: discord.Interaction):
        new_value = self.value_input.value
        all_settings = await load_settings()
        guild_id = str(self.guild_id)

        # Ensure guild entry exists
        if guild_id not in all_settings:
            all_settings[guild_id] = DEFAULT_SETTINGS.copy()

        # Convert value types properly
        if self.setting_name in ["modchannel", "welcome_channel"]:
            # expects channel mention or id
            if new_value.startswith("<#") and new_value.endswith(">"):
                new_value = int(new_value[2:-1])
            else:
                try:
                    new_value = int(new_value)
                except:
                    await interaction.response.send_message("Invalid channel input.", ephemeral=True)
                    return
        elif self.setting_name == "logging":
            new_value = new_value.lower() in ["true", "yes", "1", "on"]

        all_settings[guild_id][self.setting_name] = new_value
        await save_settings(all_settings)

        await interaction.response.send_message(
            f"✅ `{self.setting_name}` updated to `{new_value}` for this server.",
            ephemeral=True
        )


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="settings-edit", description="Edit a guild setting (Manage Server required)")
    @app_commands.describe(setting="The setting to edit")
    @app_commands.choices(setting=[
        app_commands.Choice(name=key, value=key)
        for key in DEFAULT_SETTINGS.keys()
    ])
    async def settings_edit(self, interaction: discord.Interaction, setting: app_commands.Choice[str]):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("You don’t have permission to edit settings.", ephemeral=True)
            return

        all_settings = await load_settings()
        guild_id = str(interaction.guild.id)

        if guild_id not in all_settings:
            all_settings[guild_id] = DEFAULT_SETTINGS.copy()
            await save_settings(all_settings)

        guild_settings = all_settings[guild_id]
        current_value = guild_settings.get(setting.value, "None")

        # If channel-type setting, use dropdown
        if setting.value in ["modchannel", "welcome_channel"]:
            view = ChannelSelectView(setting.value, current_value, guild_id)
            await interaction.response.send_message(
                f"Select a new channel for `{setting.value}`:",
                view=view,
                ephemeral=True
            )
        else:
            modal = SettingsModal(setting.value, str(current_value), interaction.guild.id)
            await interaction.response.send_modal(modal)


class ChannelSelectView(discord.ui.View):
    def __init__(self, setting_name, current_value, guild_id):
        super().__init__(timeout=60)
        self.setting_name = setting_name
        self.guild_id = guild_id

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text])
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        all_settings = await load_settings()
        guild_id = str(self.guild_id)

        if guild_id not in all_settings:
            all_settings[guild_id] = DEFAULT_SETTINGS.copy()

        all_settings[guild_id][self.setting_name] = channel.id
        await save_settings(all_settings)

        await interaction.response.send_message(
            f"✅ `{self.setting_name}` updated to {channel.mention}",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Moderation(bot))
