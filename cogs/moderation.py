import discord
from discord.ext import commands
from discord import app_commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = '1.0'

 
    @app_commands.command(name="ban", description="Ban a user from the server.")
    @app_commands.describe(
        member="The user to ban",
        reason="Reason for the ban"
    )
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        author = interaction.user
        guild = interaction.guild

        if not author.guild_permissions.ban_members:
            await interaction.response.send_message("You don’t have permission to ban members.", ephemeral=True)
            return

        if author.top_role <= member.top_role and author != guild.owner:
            await interaction.response.send_message("You can’t ban someone with an equal or higher role.", ephemeral=True)
            return

        if not guild.me.guild_permissions.ban_members:
            await interaction.response.send_message("I don’t have permission to ban anyone.", ephemeral=True)
            return

        if guild.me.top_role <= member.top_role:
            await interaction.response.send_message("Their role is higher than mine. I can’t ban them.", ephemeral=True)
            return

        try:
            await member.send(f"You were banned from **{guild.name}** for: {reason}")
        except:
            pass  

        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 {member.mention} has been banned.\nReason: {reason}")

    @app_commands.command(name="kick", description="Kick a user from the server.")
    @app_commands.describe(
        member="The user to kick",
        reason="Reason for the kick"
    )
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        author = interaction.user
        guild = interaction.guild

        if not author.guild_permissions.ban_members:
            await interaction.response.send_message("You don’t have permission to kick members.", ephemeral=True)
            return

        if author.top_role <= member.top_role and author != guild.owner:
            await interaction.response.send_message("You can’t kick someone with an equal or higher role.", ephemeral=True)
            return

        if not guild.me.guild_permissions.ban_members:
            await interaction.response.send_message("I don’t have permission to kick anyone.", ephemeral=True)
            return

        if guild.me.top_role <= member.top_role:
            await interaction.response.send_message("Their role is higher than mine. I can’t kick them.", ephemeral=True)
            return

        try:
            await member.send(f"You were kicked from **{guild.name}** for: {reason}")
        except:
            pass  

        await member.kick(reason=reason)
        await interaction.response.send_message(f"🔨 {member.mention} has been banned.\nReason: {reason}")


async def setup(bot):
    await bot.add_cog(Moderation(bot))

    
    


    

            
    

            
    