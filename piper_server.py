#!/usr/bin/env python3
"""
Simple Piper TTS HTTP Server

Provides an HTTP endpoint for text-to-speech using Piper.
Compatible with PiperTTSService in Pipecat.

Usage:
    python piper_server.py
    
Then configure PIPER_BASE_URL=http://localhost:5000/synthesize
"""

import asyncio
import io
import os
import wave
from pathlib import Path

from aiohttp import web
from loguru import logger

# Try to import piper
try:
    from piper import PiperVoice
except ImportError:
    logger.error("Piper not installed. Run: pip install piper-tts")
    raise

# Default voice - will be downloaded automatically
DEFAULT_VOICE = os.getenv("PIPER_VOICE", "en_US-lessac-medium")
VOICES_DIR = Path.home() / ".local" / "share" / "piper_voices"


async def download_voice(voice_name: str) -> Path:
    """Download a Piper voice model if not present."""
    import urllib.request
    
    voice_dir = VOICES_DIR / voice_name
    voice_dir.mkdir(parents=True, exist_ok=True)
    
    onnx_file = voice_dir / f"{voice_name}.onnx"
    json_file = voice_dir / f"{voice_name}.onnx.json"
    
    if onnx_file.exists() and json_file.exists():
        return onnx_file
    
    base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/"
    
    logger.info(f"Downloading voice model: {voice_name}...")
    
    if not onnx_file.exists():
        urllib.request.urlretrieve(f"{base_url}en_US-lessac-medium.onnx", onnx_file)
    
    if not json_file.exists():
        urllib.request.urlretrieve(f"{base_url}en_US-lessac-medium.onnx.json", json_file)
    
    logger.info(f"Voice downloaded to: {voice_dir}")
    return onnx_file


class PiperServer:
    def __init__(self, voice_path: Path):
        self.voice = PiperVoice.load(str(voice_path))
        logger.info(f"Loaded Piper voice: {voice_path}")
    
    async def synthesize(self, request: web.Request) -> web.Response:
        """Handle TTS synthesis requests."""
        try:
            data = await request.json()
            text = data.get("text", "")
            
            if not text:
                return web.Response(status=400, text="Missing 'text' field")
            
            logger.debug(f"Synthesizing: {text[:50]}...")
            
            # Generate audio in a thread pool
            loop = asyncio.get_event_loop()
            audio_bytes = await loop.run_in_executor(
                None, self._synthesize_sync, text
            )
            
            return web.Response(
                body=audio_bytes,
                content_type="audio/wav"
            )
            
        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            return web.Response(status=500, text=str(e))
    
    def _synthesize_sync(self, text: str) -> bytes:
        """Synchronous synthesis (runs in thread pool)."""
        # Create WAV in memory
        buffer = io.BytesIO()
        
        # Collect all audio chunks
        audio_data = b''
        sample_rate = 22050  # Default, will be updated from first chunk
        
        for chunk in self.voice.synthesize(text):
            audio_data += chunk.audio_int16_bytes
            sample_rate = chunk.sample_rate
        
        # Write WAV file
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
        
        return buffer.getvalue()


async def health(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def main():
    # Download/load voice
    voice_path = await download_voice(DEFAULT_VOICE)
    
    # Create server
    server = PiperServer(voice_path)
    
    app = web.Application()
    app.router.add_post("/synthesize", server.synthesize)
    app.router.add_get("/health", health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", 5555)
    await site.start()
    
    logger.info("Piper TTS server running on http://0.0.0.0:5555")
    logger.info("POST /synthesize with JSON body: {\"text\": \"Hello world\"}")
    
    # Keep running
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
