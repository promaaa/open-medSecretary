#!/usr/bin/env python3
#
# Copyright (c) 2024-2025
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""
Open Medical Secretary
======================

100% On-Premise medical voice assistant using Pipecat.

Components:
    - Transport: AudioSocket (Asterisk integration)
    - STT: Whisper (local, faster-whisper)
    - LLM: Ollama (local, e.g., Llama-3 or Mistral)
    - TTS: Piper (local HTTP server)
    - VAD: Silero

Usage:
    1. Start Ollama with your model:
       ollama run llama3:8b

    2. Start Piper TTS server:
       docker run -p 5000:5000 rhasspy/piper-tts-server --voice en_US-lessac-medium

    3. Run this application:
       python main.py

    4. Configure Asterisk to connect:
       exten => 1000,1,Answer()
       same => n,AudioSocket(127.0.0.1:9001,${CHANNEL(uniqueid)})
       same => n,Hangup()
"""

import asyncio
import os
import sys
from typing import Optional

import aiohttp
from dotenv import load_dotenv
from loguru import logger

# Pipecat imports
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
)
from pipecat.services.piper.tts import PiperTTSService
from pipecat.services.whisper.stt import WhisperSTTService
from pipecat.transcriptions.language import Language
from pipecat.frames.frames import TTSSpeakFrame

# Local imports
from transports.audiosocket.transport import AudioSocketTransport, AudioSocketParams
from services.medical_llm import MedicalLLMService
from config.system_prompts import MEDICAL_SYSTEM_PROMPT, GREETING_MESSAGE

# Load environment variables
load_dotenv(override=True)

# Configure logging
logger.remove(0)
logger.add(sys.stderr, level=os.getenv("LOG_LEVEL", "INFO"))


# =============================================================================
# Configuration
# =============================================================================

# AudioSocket server settings
AUDIOSOCKET_HOST = os.getenv("AUDIOSOCKET_HOST", "0.0.0.0")
AUDIOSOCKET_PORT = int(os.getenv("AUDIOSOCKET_PORT", "9001"))

# Whisper STT settings
# You can use: tiny, base, small, medium, large-v3, or HuggingFace model paths
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")  # cpu, cuda, auto
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "default")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "FR")  # EN, FR, DE, etc.

# Ollama LLM settings
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

# Piper TTS settings
PIPER_BASE_URL = os.getenv("PIPER_BASE_URL", "http://localhost:5555/synthesize")
PIPER_SAMPLE_RATE = int(os.getenv("PIPER_SAMPLE_RATE", "22050"))


# =============================================================================
# Main Application
# =============================================================================

async def main():
    """Run the medical voice assistant pipeline."""

    logger.info("=" * 60)
    logger.info("Open Medical Secretary")
    logger.info("100% On-Premise - No data sent to cloud")
    logger.info("=" * 60)

    # Create aiohttp session for Piper TTS
    async with aiohttp.ClientSession() as session:

        # -----------------------------------------------------------------
        # 1. Transport - AudioSocket for Asterisk
        # -----------------------------------------------------------------
        transport = AudioSocketTransport(
            AudioSocketParams(
                host=AUDIOSOCKET_HOST,
                port=AUDIOSOCKET_PORT,
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=SileroVADAnalyzer(
                    params=VADParams(
                        stop_secs=0.5,  # 500ms silence = end of speech
                    )
                ),
            )
        )

        logger.info(f"AudioSocket: Listening on {AUDIOSOCKET_HOST}:{AUDIOSOCKET_PORT}")

        # -----------------------------------------------------------------
        # 2. STT - Whisper (local, faster-whisper)
        # -----------------------------------------------------------------
        # Map language string to Language enum
        language_map = {"EN": Language.EN, "FR": Language.FR, "DE": Language.DE, "ES": Language.ES}
        whisper_language = language_map.get(WHISPER_LANGUAGE.upper(), Language.EN)

        stt = WhisperSTTService(
            model=WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
            language=whisper_language,
            no_speech_prob=0.4,
        )

        logger.info(f"STT: Whisper model={WHISPER_MODEL} device={WHISPER_DEVICE}")

        # -----------------------------------------------------------------
        # 3. LLM - Ollama (local)
        # -----------------------------------------------------------------
        llm = MedicalLLMService(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
        )

        logger.info(f"LLM: Ollama model={OLLAMA_MODEL} base_url={OLLAMA_BASE_URL}")

        # -----------------------------------------------------------------
        # 4. TTS - Piper (local HTTP)
        # -----------------------------------------------------------------
        tts = PiperTTSService(
            base_url=PIPER_BASE_URL,
            aiohttp_session=session,
            sample_rate=PIPER_SAMPLE_RATE,
        )

        logger.info(f"TTS: Piper base_url={PIPER_BASE_URL}")

        # -----------------------------------------------------------------
        # 5. Context - Conversation memory with medical prompt
        # -----------------------------------------------------------------
        messages = [
            {
                "role": "system",
                "content": MEDICAL_SYSTEM_PROMPT,
            }
        ]

        context = LLMContext(messages=messages)
        context_aggregator = LLMContextAggregatorPair(context)

        logger.info("Context: LLM context aggregator configured")

        # -----------------------------------------------------------------
        # 6. Pipeline - Assemble all components
        # -----------------------------------------------------------------
        pipeline = Pipeline(
            [
                transport.input(),           # Audio from Asterisk
                stt,                          # Speech-to-Text (Whisper)
                context_aggregator.user(),    # User message aggregation
                llm,                          # LLM processing (Ollama)
                tts,                          # Text-to-Speech (Piper)
                transport.output(),           # Audio to Asterisk
                context_aggregator.assistant(), # Assistant response aggregation
            ]
        )

        # -----------------------------------------------------------------
        # 7. Task - Run the pipeline
        # -----------------------------------------------------------------
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
        )

        # Register event handlers
        @transport.event_handler("on_client_connected")
        async def on_call_connected(transport, call_uuid: str):
            """Handle incoming call - say greeting."""
            logger.info(f"Call connected: {call_uuid}")
            # Queue the greeting message to be spoken
            await task.queue_frames([TTSSpeakFrame(text=GREETING_MESSAGE)])

        @transport.event_handler("on_client_disconnected")
        async def on_call_disconnected(transport, call_uuid: str):
            """Handle call end."""
            logger.info(f"Call disconnected: {call_uuid}")

        # -----------------------------------------------------------------
        # 8. Run - Start the pipeline
        # -----------------------------------------------------------------
        runner = PipelineRunner()

        logger.info("=" * 60)
        logger.info("Ready to receive calls!")
        logger.info("Configure Asterisk to point to this server.")
        logger.info("=" * 60)

        await runner.run(task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopping server...")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
