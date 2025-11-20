import discord
from discord.ext import commands
from discord import app_commands
import _encrypt as encrypt
import os
import json
import sqlite3
import asyncio
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel


class EvilSeagullCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
        #setup gpt2 (there will be a LLaMa version once trained)
        self.model_dir_gpt2 = r"C:\Users\mmati\OneDrive\Documents\GitHub\RadioCord\final-model-gpt2"  # contains adapter files
        self.base_gpt2 = "gpt2"
        self.tokenizer_gpt2 = AutoTokenizer.from_pretrained(self.base_gpt2)
        self.model_gpt2 = AutoModelForCausalLM.from_pretrained(self.base_gpt2)
        self.model_gpt2 = PeftModel.from_pretrained(self.model_gpt2, self.model_dir_gpt2)

        self.version = '1.0'

    @app_commands.command(name="evilseagull", description="Talk to the Evil Seagull AI.")
    @app_commands.describe(message="Your message to the Evil Seagull AI.", model="Choose the AI model to use.")
    @app_commands.choices(model=[
        app_commands.Choice(name="GPT-2", value="gpt2"),
        # Future models can be added here
    ])
    async def evilseagull(self, interaction: discord.Interaction, message: str, model: app_commands.Choice[str]) -> None:
        await interaction.response.defer()  # Acknowledge the command to avoid timeout

        if model.value == "gpt2":
            prompt = f"mee6: {message}\n"
            inputs = self.tokenizer_gpt2(prompt, return_tensors="pt")
            out = self.model_gpt2.generate(**inputs, max_length=100)
            response = self.tokenizer_gpt2.decode(out[0], skip_special_tokens=True)
            response = response.replace(prompt, "").strip()
        else:
            response = "Selected model is not available."
            await interaction.followup.send(response)
            return
        
        embed = discord.Embed(title="Evil Seagull AI Response", description=response, color=discord.Color.blue())
        embed.set_footer(text=f"Evil Seagull gpt2 is my child I should have aborted. LLaMa coming soon v{float(self.version) + 1}")
        await interaction.followup.send(embed=embed)
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EvilSeagullCog(bot))
