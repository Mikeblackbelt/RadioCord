import discord
import threading
import socket
import audioop
import opuslib
import struct

#TODO: INSTALL OPUS 
# Simple wrapper for audio frames
class AudioData:
    def __init__(self, pcm: bytes):
        self.pcm = pcm

# Patched VoiceClient
class PatchedVoiceClient(discord.VoiceClient):
    def start_recording(self, sink):
        if getattr(self, "_recording", False):
            return
        self._sink = sink
        self._recording = True

        # Opus decoder for 48kHz stereo
        self._decoder = opuslib.Decoder(48000, 2)

        # Start thread to receive UDP packets
        self._recv_thread = threading.Thread(target=self._recv_audio, daemon=True)
        self._recv_thread.start()

    def stop_recording(self):
        self._recording = False

    def _recv_audio(self):
        # Wait until connection is ready
        conn = self._connection
        while not getattr(conn, "_ready", False):
            continue

        udp_ip = conn.endpoint_ip
        udp_port = conn.endpoint_port
        ssrc_map = conn._ssrc_mapping  # maps SSRC to user ID

        # Create UDP socket to receive voice
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.bind(("", 0))

        while getattr(self, "_recording", False):
            try:
                packet, _ = udp_sock.recvfrom(4096)
                if not packet:
                    continue

                # Decrypt SRTP packet here
                opus_frame = self._decrypt_srtp(packet, conn.secret_key)

                # Decode Opus to PCM
                pcm = self._decoder.decode(opus_frame, 960)  # 20ms frame
                pcm = audioop.tostereo(pcm, 2, 1, 1)

                # Map SSRC to user
                ssrc = struct.unpack(">I", packet[8:12])[0]
                user = conn._get_user_from_ssrc(ssrc)
                if user:
                    self._sink.write(user, AudioData(pcm))

            except Exception:
                continue

    def _decrypt_srtp(self, packet: bytes, key: bytes) -> bytes:
        # Minimal placeholder: implement SRTP decryption here
        # You need to decrypt using libsrtp or PyNaCl
        return packet[12:]  # naive: skip RTP header for testing only
