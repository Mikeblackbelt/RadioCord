import huggingface_hub
from huggingface_hub import InferenceClient
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import json
import pyttsx3
import uuid

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
client = InferenceClient(provider='novita', token=HF_TOKEN)

engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

class LLM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ask", description="Ask a question to the AI.")
    @app_commands.describe(question="Your question")
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        try:
            user_id = str(interaction.user.id)
            with open("cogs/_context_.json", "r") as f:
                config = json.load(f)

            if user_id in config:
                context = config[user_id]
            else:
                context = []

            prompt = "\n".join(context + [f"User: {question}", "AI:"])
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.1-8B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512)
            context.append(f"User: {question}")
            context.append(f"AI: {response.choices[0].message['content']}")
            config[user_id] = context[-10:]
            with open("cogs/_context_.json", "w") as f:
                json.dump(config, f, indent=4)
            answer = response.choices[0].message['content'].strip()
            if not answer:
                answer = "I'm sorry, I couldn't generate a response."
            embed = discord.Embed(title="AI Response", description=answer, color=discord.Color.blue())
            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(title="Error", description=f"Could not process your request.\nPlease Report this Error: {str(e)}", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="speak", description="Ask a question and get an audio response.")
    @app_commands.describe(question="Your question")
    async def speak(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        try:
            user_id = str(interaction.user.id)
            with open("cogs/_context_.json", "r") as f:
                config = json.load(f)

            if user_id in config:
                context = config[user_id]
            else:
                context = []

            prompt = "\n".join(context + [f"User: {question}", "AI:"])
            print(prompt)
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.1-8B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512)
            context.append(f"RESPOND WITH ONLY A MAXIMUM OF 2-3 SENTENCES: \nUser: {question}")
            context.append(f"AI: {response.choices[0].message['content']}")
            config[user_id] = context[-10:]
            with open("cogs/_context_.json", "w") as f:
                json.dump(config, f, indent=4)
            answer = response.choices[0].message['content'].strip()
            print(f"AI Answer: {answer}")
            if not answer:
                answer = "I'm sorry, I couldn't generate a response."

            filename = f"response_{uuid.uuid4().hex}.mp3"
            print(f"Generating audio file: {filename}")
            engine.save_to_file(answer, filename)
            engine.runAndWait()
            print(f"Audio file generated: {filename}")
            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send("You’re not in a voice channel.", ephemeral=True)
                os.remove(filename)
                return

            channel = interaction.user.voice.channel
            vc = interaction.guild.voice_client
            if not vc:
                vc = await channel.connect()
            elif vc.channel != channel:
                await vc.move_to(channel)

            if vc.is_playing():
                vc.stop()

            vc.play(discord.FFmpegPCMAudio(filename), after=lambda e: print(f"Finished playing: {e}" if e else "Finished playing."))

            embed = discord.Embed(title="AI Audio Response", description="Playing the audio response in your voice channel.", color=discord.Color.purple())
            await interaction.followup.send(embed=embed)

            def remove_file(error):
                try:
                    os.remove(filename)
                    print(f"Removed file: {filename}")
                except Exception as e:
                    print(f"Error removing file {filename}: {e}")

            vc.play(discord.FFmpegPCMAudio(filename), after=remove_file)
        except Exception as e:
            embed = discord.Embed(title="Error", description=f"Could not process your request.\nPlease Report this Error: {str(e)}", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="study", description="Study a subject with the help of the AI.")
    async def study(self, interaction: discord.Interaction, subject: str):
        await interaction.response.defer()
        try:
            user_id = str(interaction.user.id)
            with open("cogs/_context_.json", "r") as f:
                config = json.load(f)

            if user_id in config:
                context = config[user_id]
            else:
                context = []

            prompt = "\n".join(context + [f"User: I want to study {subject}. Help me learn about it, and give 3 practice problems at the end..", "AI:"])
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.1-8B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512)
            context.append(f"User: I want to study {subject}. Help me learn about it.")
            context.append(f"AI: {response.choices[0].message['content']}")
            config[user_id] = context[-10:]
            with open("cogs/_context_.json", "w") as f:
                json.dump(config, f, indent=4)
            answer = response.choices[0].message['content'].strip()
            if not answer:
                answer = "I'm sorry, I couldn't generate a response."
            embed = discord.Embed(title=f"Study Session: {subject}", description=answer, color=discord.Color.teal())
            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(title="Error", description=f"Could not process your request.\nPlease Report this Error: {str(e)}", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):  
        await bot.add_cog(LLM(bot))
        print("LLM Cog Loaded")

