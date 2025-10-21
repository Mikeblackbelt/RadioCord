import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import json
import uuid
import asyncio
from huggingface_hub import InferenceClient
from gtts import gTTS
import aiofiles

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
client = InferenceClient(provider='novita', token=HF_TOKEN)

# Lock per guild for VC commands to avoid race conditions
guild_locks = {}

async def get_guild_lock(guild_id: int):
    if guild_id not in guild_locks:
        guild_locks[guild_id] = asyncio.Lock()
    return guild_locks[guild_id]

# Async TTS generation using gTTS
async def generate_audio(text: str, filename: str):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: gTTS(text).save(filename))

# Async JSON read/write
async def read_context():
    try:
        async with aiofiles.open("cogs/_context_.json", "r") as f:
            data = await f.read()
            return json.loads(data)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

async def write_context(config):
    async with aiofiles.open("cogs/_context_.json", "w") as f:
        await f.write(json.dumps(config, indent=4))

class LLM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = "2.0"

    # ---------- Ask Command ----------
    @app_commands.command(name="ask", description="Ask a question to the AI.")
    @app_commands.describe(question="Your question")
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        try:
            user_id = str(interaction.user.id)
            config = await read_context()
            context = config.get(user_id, [])

            prompt = "\n".join(context + [f"User: {question}", "AI:"])
            
            # Hugging Face API in thread to avoid blocking
            response = await asyncio.to_thread(lambda: client.chat.completions.create(
                model="meta-llama/Llama-3.1-8B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512
            ))

            answer_text = response.choices[0].message["content"].strip() or "I'm sorry, I couldn't generate a response."
            context.append(f"User: {question}")
            context.append(f"AI: {answer_text}")
            config[user_id] = context[-35:]  # Trim context
            await write_context(config)

            embed = discord.Embed(title="AI Response", description=answer_text, color=discord.Color.blue())
            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(title="Error", description=f"Could not process your request.\n{e}", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ---------- Speak Command ----------
    @app_commands.command(name="speak", description="Ask a question and get an audio response.")
    @app_commands.describe(question="Your question")
    async def speak(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        try:
            user_id = str(interaction.user.id)
            config = await read_context()
            context = config.get(user_id, [])

            prompt = "\n".join(context + [f"User: {question}", "AI:"])
            print(f"Prompt:\n{prompt}")

            # Hugging Face API async
            response = await asyncio.to_thread(lambda: client.chat.completions.create(
                model="meta-llama/Llama-3.1-8B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512
            ))

            answer_text = response.choices[0].message["content"].strip() or "I'm sorry, I couldn't generate a response."
            context.append(f"User: {question}")
            context.append(f"AI: {answer_text}")
            config[user_id] = context[-10:]  # Trim context
            await write_context(config)

            # Generate audio file
            filename = f"response_{uuid.uuid4().hex}.mp3"
            await generate_audio(answer_text, filename)
            print(f"Generated audio: {filename}")

            if not interaction.user.voice or not interaction.user.voice.channel:
                await interaction.followup.send("You must be in a voice channel to play audio.", ephemeral=True)
                os.remove(filename)
                return

            channel = interaction.user.voice.channel
            lock = await get_guild_lock(interaction.guild.id)

            async with lock:
                vc = interaction.guild.voice_client
                if not vc:
                    vc = await channel.connect()
                elif vc.channel != channel:
                    await vc.move_to(channel)

                if vc.is_playing():
                    vc.stop()

                def remove_file(error):
                    try:
                        os.remove(filename)
                        print(f"Removed file: {filename}")
                    except Exception as e:
                        print(f"Error removing file {filename}: {e}")

                vc.play(discord.FFmpegPCMAudio(filename), after=remove_file)

            embed = discord.Embed(title="AI Audio Response", description="Playing audio in your voice channel.", color=discord.Color.purple())
            await interaction.followup.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(title="Error", description=f"Could not process your request.\n{e}", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

    # ---------- Study Command ----------
    @app_commands.command(name="study", description="Study a subject with the help of the AI.")
    @app_commands.describe(subject="The subject you want to study")
    async def study(self, interaction: discord.Interaction, subject: str):
        await interaction.response.defer()
        try:
            user_id = str(interaction.user.id)
            config = await read_context()
            context = config.get(user_id, [])

            prompt = "\n".join(context + [f"User: I want to study {subject}. Help me learn and give 3 practice problems.", "AI:"])
            response = await asyncio.to_thread(lambda: client.chat.completions.create(
                model="meta-llama/Llama-3.1-8B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512
            ))

            answer_text = response.choices[0].message["content"].strip() or "I'm sorry, I couldn't generate a response."
            context.append(f"User: I want to study {subject}")
            context.append(f"AI: {answer_text}")
            config[user_id] = context[-35:]
            await write_context(config)

            embed = discord.Embed(title=f"Study Session: {subject}", description=answer_text, color=discord.Color.teal())
            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(title="Error", description=f"Could not process your request.\n{e}", color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)

# Setup function for cog
async def setup(bot):
    cog = LLM(bot)
    await bot.add_cog(cog)
    embed = discord.Embed(title="LLM Cog Loaded", description=f"Version: {cog.version}\nCommands: {cog.get_app_commands()}")
    update_channel = bot.get_channel(1428731822442811403)
    if update_channel:
        await update_channel.send(embed=embed)
