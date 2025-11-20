import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import io
import wave
import audioop

# AudioSink to collect audio
class AudioSink:
    def __init__(self):
        self.finished = asyncio.Event()
        self.audio_buffer = b""

    def write(self, user, data):
        # 'data' is expected to have .pcm from PatchedVoiceClient
        if data and hasattr(data, "pcm"):
            self.audio_buffer += data.pcm

    def get_wav(self):
        # Write collected PCM to WAV
        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as wav_file:
                wav_file.setnchannels(2)  # stereo
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(48000)
                wav_file.writeframes(self.audio_buffer)
            buffer.seek(0)
            return buffer.read()


class Convo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = '0.3'

    @app_commands.command(name="convo", description="Record voice and detect silence.")
    async def convo(self, interaction: discord.Interaction):
        user = interaction.user
        if not user.voice or not user.voice.channel:
            return await interaction.response.send_message(
                "You need to be in a voice channel.", ephemeral=True
            )

        await interaction.response.defer(thinking=True)
        channel = user.voice.channel

        # Connect to voice
        vc = await channel.connect(timeout=120,self_deaf=False,self_mute=False)
        sink = AudioSink()
        await interaction.followup.send("🎙️ Listening... start talking.")

        # Use your patched VC's recording methods
        if hasattr(vc, "start_recording"):
            vc.start_recording(sink)
        else:
            await interaction.followup.send(
                "⚠️ Voice receiving not supported in this version."
            )
            await vc.disconnect()
            return

        silence_threshold = 3  # seconds
        last_audio_time = asyncio.get_event_loop().time()
        last_buffer_len = 0

        # Wait until user stops speaking
        while True:
            await asyncio.sleep(1)
            if len(sink.audio_buffer) > last_buffer_len:
                last_buffer_len = len(sink.audio_buffer)
                last_audio_time = asyncio.get_event_loop().time()
            elif asyncio.get_event_loop().time() - last_audio_time > silence_threshold:
                break

        # Stop recording
        vc.stop_recording()
        await interaction.followup.send("🛑 You stopped speaking. Saving audio...")

        wav_data = sink.get_wav()
        filename = f"user_audio_{user.id}.wav"
        with open(filename, "wb") as f:
            f.write(wav_data)

        await interaction.followup.send(f"✅ Audio saved as `{filename}`")
        await vc.disconnect()


async def setup(bot):
    await bot.add_cog(Convo(bot))
