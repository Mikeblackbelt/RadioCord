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
import random
import aiofiles

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
client = InferenceClient(provider='novita', token=HF_TOKEN)

guild_locks = {}

async def get_guild_lock(guild_id: int):
    if guild_id not in guild_locks:
        guild_locks[guild_id] = asyncio.Lock()
    return guild_locks[guild_id]

async def read_json(file):
    try:
        async with aiofiles.open(file, "r") as f:
            return json.loads(await f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

async def write_json(file, data):
    async with aiofiles.open(file, "w") as f:
        await f.write(json.dumps(data, indent=4))

async def read_context():
    return await read_json("cogs/_context_.json")

async def write_context(config):
    await write_json("cogs/_context_.json", config)

async def read_dungeon():
    return await read_json("cogs/_dungeon.json")

async def write_dungeon(data):
    await write_json("cogs/_dungeon.json", data)

async def generate_audio(text, filename):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, lambda: gTTS(text).save(filename))

class DungeonActionModal(discord.ui.Modal):
    def __init__(self, user_id, player, dungeon):
        super().__init__(title="Enter Your Action")
        self.user_id = user_id
        self.player = player
        self.dungeon = dungeon
        self.action_input = discord.ui.TextInput(label="What do you do?", placeholder="Type your action here")
        self.add_item(self.action_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        command = self.action_input.value.strip()
        if not command:
            return await interaction.followup.send("You must enter an action!", ephemeral=True)

        self.player["chapter"] += 1
        self.player["history"].append(f"Player: {command}")

        roll = random.randint(1, 20)
        prompt = (
            "SYSTEM: You are the Dungeon Master. Continue the story in 2-5 sentences. "
            f"Player did: {command}. Dice roll: D{roll}. "
            "If used, start with 'You rolled a **D{roll}**'. "
            "Conclude the story within ~20 chapters. End with 'THE END' if finished.\n\n"
            "Story so far:\n" + "\n".join(self.player["history"]) + "\n\nContinue:"
        )

        response = await asyncio.to_thread(lambda: client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400
        ))

        text = response.choices[0].message["content"].strip()
        self.player["history"].append(text)
        if "THE END" in text:
            self.player["active"] = False

        self.dungeon["players"][self.user_id] = self.player
        await write_dungeon(self.dungeon)

        story_text = "\n".join(self.player["history"][-1:])

        embed = discord.Embed(
            title=f"📖 Chapter {self.player['chapter']}",
            description=story_text,
            color=0x3498DB
        )
        embed.set_footer(text="Adventure concluded." if not self.player["active"] else "Use Continue button for next action.")

        await interaction.followup.send(
            embed=embed,
            view=None if not self.player["active"] else DungeonButtons(self.user_id, self.player, self.dungeon)
        )

class DungeonButtons(discord.ui.View):
    def __init__(self, user_id, player, dungeon):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.player = player
        self.dungeon = dungeon

    @discord.ui.button(label="Continue", style=discord.ButtonStyle.primary)
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This is not your adventure!", ephemeral=True)
        await interaction.response.send_modal(DungeonActionModal(self.user_id, self.player, self.dungeon))

    @discord.ui.button(label="End Adventure", style=discord.ButtonStyle.danger)
    async def end_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if the user is the correct player
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("This is not your adventure!", ephemeral=True)
        
        # Defer the response
        await interaction.response.defer()

        # Generate ending
        prompt = (
            "SYSTEM: You are the Dungeon Master. The player has chosen to end early. "
            "Write a satisfying conclusion in 2-5 sentences and end with 'THE END'.\n\n"
            "Story so far:\n" + "\n".join(self.player["history"])
        )

        response = await asyncio.to_thread(lambda: client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        ))

        text = response.choices[0].message["content"].strip()
        self.player["history"].append(text)
        self.player["active"] = False
        self.dungeon["players"][self.user_id] = self.player
        await write_dungeon(self.dungeon)

        # Disable all buttons after ending
        for child in self.children:
            child.disabled = True

        embed = discord.Embed(title="🏁 Adventure Ended", description=text, color=0xE74C3C)
        embed.set_footer(text="You can start a new adventure with /dungeon start.")
        await interaction.followup.send(embed=embed, view=self)


class LLM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = "2.0"

    @app_commands.command(name="dungeon", description="Single-player AI-driven dungeon adventure")
    @app_commands.describe(action="Start or resume", plot="Optional plot for start")
    @app_commands.choices(action=[
        app_commands.Choice(name="Start", value=1),
        app_commands.Choice(name="Resume", value=2)
    ])
    async def dungeon(self, interaction: discord.Interaction, action: app_commands.Choice[int], plot: str = None):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        dungeon_data = await read_dungeon()
        if "players" not in dungeon_data: dungeon_data["players"] = {}
        player = dungeon_data["players"].get(user_id, {"active": False, "chapter": 0, "history": []})

        if action.value == 1:
            player["active"] = True
            player["chapter"] = 1
            player["history"] = ["The adventure begins."]
            dungeon_data["players"][user_id] = player
            await write_dungeon(dungeon_data)

            prompt = f"SYSTEM: You are a Dungeon Master. Introduce a story for the player. Theme: {plot}. Keep it 2-5 sentences.\nStart:"
            response = await asyncio.to_thread(lambda: client.chat.completions.create(
                model="meta-llama/Llama-3.1-8B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            ))
            text = response.choices[0].message["content"].strip()
            player["history"].append(text)
            dungeon_data["players"][user_id] = player
            await write_dungeon(dungeon_data)

            embed = discord.Embed(title="🗡️ Dungeon Adventure Started!", description="\n".join(player["history"][-6:]), color=0x9B59B6)
            embed.set_footer(text="Use the buttons below to continue your adventure.")
            await interaction.followup.send(embed=embed, view=DungeonButtons(user_id, player, dungeon_data))

        elif action.value == 2:
            if not player["active"]:
                return await interaction.followup.send("❌ You have no active adventure. Use /dungeon start.")
            embed = discord.Embed(title=f"📖 Chapter {player['chapter']}", description="\n".join(player["history"][-6:]), color=0x3498DB)
            embed.set_footer(text="Use the buttons below to continue or end your adventure.")
            await interaction.followup.send(embed=embed, view=DungeonButtons(user_id, player, dungeon_data))

    @app_commands.command(name="ask", description="Ask a question to the AI.")
    @app_commands.describe(question="Your question")
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        config = await read_context()
        context = config.get(user_id, [])
        prompt = f"SYSTEM: You are RadioCord, a Discord AI bot. Previous context:\n" + "\n".join(context) + f"\n\nUser: {question}\nAI:"

        response = await asyncio.to_thread(lambda: client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512
        ))

        answer_text = response.choices[0].message["content"].strip()
        context.append(f"User: {question}")
        context.append(f"AI: {answer_text}")
        config[user_id] = context[-35:]
        await write_context(config)

        embed = discord.Embed(title="AI Response", description=answer_text, color=discord.Color.blue())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="speak", description="Ask a question and get an audio response.")
    @app_commands.describe(question="Your question")
    async def speak(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        config = await read_context()
        context = config.get(user_id, [])
        prompt = "\n".join(context + [f"User: {question}", "AI:"])

        response = await asyncio.to_thread(lambda: client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512
        ))

        answer_text = response.choices[0].message["content"].strip()
        context.append(f"User: {question}")
        context.append(f"AI: {answer_text}")
        config[user_id] = context[-10:]
        await write_context(config)

        filename = f"response_{uuid.uuid4().hex}.mp3"
        await generate_audio(answer_text, filename)

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("You must be in a voice channel.", ephemeral=True)
            os.remove(filename)
            return

        channel = interaction.user.voice.channel
        lock = await get_guild_lock(interaction.guild.id)
        async with lock:
            vc = interaction.guild.voice_client
            if not vc: vc = await channel.connect()
            elif vc.channel != channel: await vc.move_to(channel)
            if vc.is_playing(): vc.stop()
            def remove_file(error): 
                try: os.remove(filename)
                except: pass
            vc.play(discord.FFmpegPCMAudio(filename), after=remove_file)

        embed = discord.Embed(title="AI Audio Response", description="Playing in VC", color=discord.Color.purple())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="study", description="Study a subject with AI assistance.")
    @app_commands.describe(subject="The subject you want to study")
    async def study(self, interaction: discord.Interaction, subject: str):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        config = await read_context()
        context = config.get(user_id, [])
        prompt = "\n".join(context + [f"SYSTEM: DO NOT BE SARCASTIC FOR THIS\nUser: I want to study {subject}. Give 3 practice problems.", "AI:"])

        response = await asyncio.to_thread(lambda: client.chat.completions.create(
            model="meta-llama/Llama-3.1-8B-Instruct",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512
        ))

        answer_text = response.choices[0].message["content"].strip()
        context.append(f"User: I want to study {subject}")
        context.append(f"AI: {answer_text}")
        config[user_id] = context[-35:]
        await write_context(config)

        embed = discord.Embed(title=f"Study Session: {subject}", description=answer_text, color=discord.Color.teal())
        await interaction.followup.send(embed=embed)

async def setup(bot):
    cog = LLM(bot)
    await bot.add_cog(cog)
    update_channel = bot.get_channel(1428731822442811403)
    if update_channel:
        embed = discord.Embed(title="LLM Cog Loaded", description=f"Version: {cog.version}\nCommands: {cog.get_app_commands()}")
        await update_channel.send(embed=embed)
