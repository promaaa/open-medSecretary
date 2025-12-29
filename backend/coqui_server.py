#!/usr/bin/env python3
"""
Coqui TTS HTTP Server

Provides an HTTP endpoint for text-to-speech using Coqui TTS.
Uses VITS models which are fast and produce natural-sounding speech.

Usage:
    python coqui_server.py
    
Then configure PIPER_BASE_URL=http://localhost:5555/synthesize
(Uses same API format as Piper for compatibility)
"""

import asyncio
import io
import os
import wave

from aiohttp import web
from loguru import logger

# Coqui TTS
try:
    from TTS.api import TTS
except ImportError:
    logger.error("Coqui TTS not installed. Run: pip install TTS")
    raise

# Configuration
HOST = os.getenv("TTS_HOST", "0.0.0.0")
PORT = int(os.getenv("TTS_PORT", "5555"))

# Available French models (fast to slow, quality increasing):
# - "tts_models/fr/mai/tacotron2-DDC" - Fast, decent quality
# - "tts_models/fr/css10/vits" - Very fast, good quality (recommended)
# - "tts_models/multilingual/multi-dataset/xtts_v2" - Slow, excellent quality, requires GPU
MODEL_NAME = os.getenv("TTS_MODEL", "tts_models/fr/css10/vits")


class CoquiTTSServer:
    def __init__(self):
        logger.info(f"Loading Coqui TTS model: {MODEL_NAME}")
        logger.info("This may take a moment on first run (downloading model)...")
        
        # Initialize TTS - will download model on first run
        self.tts = TTS(MODEL_NAME)
        
        # Get sample rate from model config
        self.sample_rate = self.tts.synthesizer.output_sample_rate
        logger.info(f"Model loaded. Sample rate: {self.sample_rate}Hz")
    
    async def synthesize(self, request: web.Request) -> web.Response:
        """Handle TTS synthesis requests."""
        try:
            data = await request.json()
            text = data.get("text", "")
            
            if not text:
                return web.Response(status=400, text="Missing 'text' field")
            
            logger.debug(f"Synthesizing: {text[:50]}...")
            
            # Generate audio in a thread pool (TTS is CPU-bound)
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
        # Synthesize to numpy array
        wav = self.tts.tts(text)
        
        # Convert to bytes
        import numpy as np
        audio_int16 = (np.array(wav) * 32767).astype(np.int16)
        
        # Create WAV in memory
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        return buffer.getvalue()


async def health(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def main():
    # Create server
    server = CoquiTTSServer()
    
    app = web.Application()
    app.router.add_post("/synthesize", server.synthesize)
    app.router.add_get("/health", health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    
    logger.info(f"Coqui TTS server running on http://{HOST}:{PORT}")
    logger.info(f"Model: {MODEL_NAME}")
    logger.info("POST /synthesize with JSON body: {\"text\": \"Bonjour\"}")
    
    # Keep running
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
