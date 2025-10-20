import discord
from discord import app_commands
from discord.ext import commands, voice_recv
import asyncio
import io
import wave
import whisper

class AudioSink(voice_recv.BasicSink):
    def __init__(self):
        self.finished = asyncio.Event()
        super().__init__(self.finished)
        self.audio_buffer = b""

    def write(self, user, data):
        if data and data.pcm:
            self.audio_buffer += data.pcm

    def get_wav(self):
        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as wav_file:
                wav_file.setnchannels(2)
                wav_file.setsampwidth(2)
                wav_file.setframerate(48000)
                wav_file.writeframes(self.audio_buffer)
            buffer.seek(0)
            return buffer.read()

class Convo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.model = whisper.load_model("medium")

    @app_commands.command(name="convo", description="Start a voice convo and detect silence.")
    async def convo(self, interaction: discord.Interaction):
        user = interaction.user
        if not user.voice:
            return await interaction.response.send_message("You need to be in a voice channel.", ephemeral=True)

        await interaction.response.defer(thinking=True)
        channel = user.voice.channel
        vc = await channel.connect(cls=voice_recv.VoiceRecvClient)
        sink = AudioSink()

        await interaction.followup.send("🎙️ Listening... start talking.")
        vc.listen(sink)

        silence_threshold = 3  # seconds
        last_audio_time = asyncio.get_event_loop().time()
        last_buffer_len = 0

        while True:
            await asyncio.sleep(1)
            if len(sink.audio_buffer) > last_buffer_len:
                last_buffer_len = len(sink.audio_buffer)
                last_audio_time = asyncio.get_event_loop().time()
            elif asyncio.get_event_loop().time() - last_audio_time > silence_threshold:
                break

        vc.stop_listening()
        await interaction.followup.send("🛑 You stopped speaking. Processing...")

        wav_data = sink.get_wav()
        with open("user_audio.wav", "wb") as f:
            f.write(wav_data)

        try:
            result = self.model.transcribe("user_audio.wav")
            text = result["text"].strip()
            if text:
                await interaction.followup.send(f"🗣️ Transcription: `{text}`")
            else:
                await interaction.followup.send("I didn’t catch anything clear enough to transcribe.")
        except Exception as e:
            await interaction.followup.send(f"Something broke while processing: `{e}`")

        await vc.disconnect()

async def setup(bot):
    await bot.add_cog(Convo(bot))
