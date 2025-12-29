#
# Copyright (c) 2024-2025
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""AudioSocket transport implementation for Asterisk integration.

This module provides TCP AudioSocket transport functionality for connecting
Pipecat pipelines to Asterisk PBX systems via the AudioSocket application.

AudioSocket Protocol:
    - 3 byte header: [type (1 byte)][length (2 bytes big-endian)]
    - Types: 0x00=Terminate, 0x01=UUID, 0x10=Audio, 0x11=Silence
    - Audio: 16-bit signed PCM, 8kHz mono (from Asterisk)
"""

import asyncio
import struct
from typing import Awaitable, Callable, Optional

import numpy as np
from loguru import logger
from pydantic import BaseModel

from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    StartFrame,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.transports.base_input import BaseInputTransport
from pipecat.transports.base_output import BaseOutputTransport
from pipecat.transports.base_transport import BaseTransport, TransportParams

try:
    from scipy import signal
except ModuleNotFoundError as e:
    logger.error(f"Exception: {e}")
    logger.error("Install scipy for audio resampling: pip install scipy")
    raise Exception(f"Missing module: {e}")


# AudioSocket packet types
AUDIOSOCKET_TYPE_TERMINATE = 0x00
AUDIOSOCKET_TYPE_UUID = 0x01
AUDIOSOCKET_TYPE_AUDIO = 0x10
AUDIOSOCKET_TYPE_SILENCE = 0x11

# Audio format constants
ASTERISK_SAMPLE_RATE = 8000  # Asterisk AudioSocket uses 8kHz
PIPECAT_SAMPLE_RATE = 16000  # Pipecat default is 16kHz


class AudioSocketParams(TransportParams):
    """Configuration parameters for AudioSocket transport.

    Parameters:
        host: Host address to bind the TCP server to.
        port: Port number to bind the TCP server to.
        asterisk_sample_rate: Sample rate from Asterisk (default 8000).
        pipeline_sample_rate: Sample rate for Pipecat pipeline (default 16000).
    """

    host: str = "0.0.0.0"
    port: int = 9001
    asterisk_sample_rate: int = ASTERISK_SAMPLE_RATE
    pipeline_sample_rate: int = PIPECAT_SAMPLE_RATE


class AudioSocketCallbacks(BaseModel):
    """Callback functions for AudioSocket events.

    Parameters:
        on_client_connected: Called when Asterisk connects with call UUID.
        on_client_disconnected: Called when Asterisk disconnects.
    """

    class Config:
        arbitrary_types_allowed = True

    on_client_connected: Callable[[str], Awaitable[None]]
    on_client_disconnected: Callable[[str], Awaitable[None]]


def resample_audio(audio: bytes, from_rate: int, to_rate: int) -> bytes:
    """Resample audio from one sample rate to another.

    Args:
        audio: Raw audio bytes (16-bit signed PCM).
        from_rate: Source sample rate in Hz.
        to_rate: Target sample rate in Hz.

    Returns:
        Resampled audio bytes (16-bit signed PCM).
    """
    if from_rate == to_rate:
        return audio

    # Convert bytes to numpy array
    audio_array = np.frombuffer(audio, dtype=np.int16)

    # Calculate resampling ratio
    num_samples = int(len(audio_array) * to_rate / from_rate)

    # Resample using scipy
    resampled = signal.resample(audio_array, num_samples)

    # Convert back to int16 bytes
    return resampled.astype(np.int16).tobytes()


class AudioSocketInputTransport(BaseInputTransport):
    """AudioSocket input transport for receiving audio from Asterisk.

    Handles incoming TCP connections from Asterisk, parses AudioSocket packets,
    resamples audio from 8kHz to 16kHz, and pushes InputAudioRawFrames to the pipeline.
    """

    def __init__(
        self,
        transport: BaseTransport,
        params: AudioSocketParams,
        callbacks: AudioSocketCallbacks,
        **kwargs,
    ):
        """Initialize the AudioSocket input transport.

        Args:
            transport: The parent transport instance.
            params: AudioSocket configuration parameters.
            callbacks: Callback functions for AudioSocket events.
            **kwargs: Additional arguments passed to parent class.
        """
        super().__init__(params, **kwargs)

        self._transport = transport
        self._params = params
        self._callbacks = callbacks

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._server: Optional[asyncio.Server] = None

        self._call_uuid: Optional[str] = None
        self._server_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None

        self._stop_server_event = asyncio.Event()
        self._initialized = False

    async def start(self, frame: StartFrame):
        """Start the AudioSocket server and initialize components.

        Args:
            frame: The start frame containing initialization parameters.
        """
        await super().start(frame)

        if self._initialized:
            return

        self._initialized = True

        if not self._server_task:
            self._server_task = self.create_task(self._server_task_handler())
        await self.set_transport_ready(frame)

    async def stop(self, frame: EndFrame):
        """Stop the AudioSocket server and cleanup resources.

        Args:
            frame: The end frame signaling transport shutdown.
        """
        await super().stop(frame)
        self._stop_server_event.set()

        if self._receive_task:
            await self.cancel_task(self._receive_task)
            self._receive_task = None

        if self._server_task:
            await self._server_task
            self._server_task = None

        await self._close_client_connection()

    async def cancel(self, frame: CancelFrame):
        """Cancel the AudioSocket server and stop all processing.

        Args:
            frame: The cancel frame signaling immediate cancellation.
        """
        await super().cancel(frame)

        if self._receive_task:
            await self.cancel_task(self._receive_task)
            self._receive_task = None

        if self._server_task:
            await self.cancel_task(self._server_task)
            self._server_task = None

        await self._close_client_connection()

    async def cleanup(self):
        """Cleanup resources and parent transport."""
        await super().cleanup()
        await self._transport.cleanup()

    async def _server_task_handler(self):
        """Handle TCP server startup and client connections."""
        logger.info(f"Starting AudioSocket server on {self._params.host}:{self._params.port}")

        self._server = await asyncio.start_server(
            self._client_handler, self._params.host, self._params.port
        )

        async with self._server:
            await self._stop_server_event.wait()

        logger.info("AudioSocket server stopped")

    async def _client_handler(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """Handle individual client connections from Asterisk."""
        addr = writer.get_extra_info("peername")
        logger.info(f"New Asterisk connection from {addr}")

        # Only allow one connection at a time
        if self._reader is not None:
            logger.warning("Only one Asterisk connection allowed, closing previous")
            await self._close_client_connection()

        self._reader = reader
        self._writer = writer

        # Start receiving audio packets
        self._receive_task = self.create_task(self._receive_packets())

    async def _close_client_connection(self):
        """Close the current client connection."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as e:
                logger.debug(f"Error closing writer: {e}")
            self._writer = None

        self._reader = None

        if self._call_uuid:
            await self._callbacks.on_client_disconnected(self._call_uuid)
            self._call_uuid = None

    async def _receive_packets(self):
        """Receive and process AudioSocket packets from Asterisk."""
        try:
            while self._reader and not self._reader.at_eof():
                # Read 3-byte header
                header = await self._reader.readexactly(3)
                packet_type = header[0]
                payload_length = struct.unpack(">H", header[1:3])[0]

                # Read payload
                payload = b""
                if payload_length > 0:
                    payload = await self._reader.readexactly(payload_length)

                # Process packet based on type
                if packet_type == AUDIOSOCKET_TYPE_TERMINATE:
                    logger.info("Received TERMINATE packet, call ended")
                    break

                elif packet_type == AUDIOSOCKET_TYPE_UUID:
                    self._call_uuid = payload.decode("utf-8").strip()
                    logger.info(f"Call UUID: {self._call_uuid}")
                    await self._callbacks.on_client_connected(self._call_uuid)

                elif packet_type == AUDIOSOCKET_TYPE_AUDIO:
                    await self._handle_audio_packet(payload)

                elif packet_type == AUDIOSOCKET_TYPE_SILENCE:
                    # Generate silence frames if needed (optional)
                    pass

        except asyncio.IncompleteReadError:
            logger.info("Asterisk connection closed (incomplete read)")
        except asyncio.CancelledError:
            logger.info("Receive task cancelled")
            raise
        except Exception as e:
            logger.error(f"Error receiving AudioSocket packets: {e}")
        finally:
            await self._close_client_connection()

    async def _handle_audio_packet(self, audio_data: bytes):
        """Process an audio packet from Asterisk.

        Args:
            audio_data: Raw audio bytes (16-bit PCM, 8kHz mono).
        """
        # Resample from Asterisk rate (8kHz) to pipeline rate (16kHz)
        resampled_audio = resample_audio(
            audio_data,
            self._params.asterisk_sample_rate,
            self._params.pipeline_sample_rate,
        )

        # Create and push input frame
        frame = InputAudioRawFrame(
            audio=resampled_audio,
            sample_rate=self._params.pipeline_sample_rate,
            num_channels=1,
        )
        await self.push_audio_frame(frame)


class AudioSocketOutputTransport(BaseOutputTransport):
    """AudioSocket output transport for sending audio to Asterisk.

    Handles outgoing audio frames from the pipeline, resamples from 16kHz to 8kHz,
    encodes to AudioSocket format, and sends to Asterisk.
    """

    def __init__(
        self,
        transport: BaseTransport,
        params: AudioSocketParams,
        **kwargs,
    ):
        """Initialize the AudioSocket output transport.

        Args:
            transport: The parent transport instance.
            params: AudioSocket configuration parameters.
            **kwargs: Additional arguments passed to parent class.
        """
        super().__init__(params, **kwargs)

        self._transport = transport
        self._params = params

        self._writer: Optional[asyncio.StreamWriter] = None
        self._initialized = False

    def set_writer(self, writer: Optional[asyncio.StreamWriter]):
        """Set the TCP writer for sending audio to Asterisk.

        Args:
            writer: The StreamWriter to use, or None to clear.
        """
        self._writer = writer

    async def start(self, frame: StartFrame):
        """Start the output transport and initialize components.

        Args:
            frame: The start frame containing initialization parameters.
        """
        await super().start(frame)

        if self._initialized:
            return

        self._initialized = True
        await self.set_transport_ready(frame)

    async def stop(self, frame: EndFrame):
        """Stop the output transport.

        Args:
            frame: The end frame signaling transport shutdown.
        """
        await super().stop(frame)
        # Send terminate packet
        await self._send_terminate()

    async def cancel(self, frame: CancelFrame):
        """Cancel the output transport.

        Args:
            frame: The cancel frame signaling immediate cancellation.
        """
        await super().cancel(frame)

    async def cleanup(self):
        """Cleanup resources and parent transport."""
        await super().cleanup()
        await self._transport.cleanup()

    async def write_audio_frame(self, frame: OutputAudioRawFrame) -> bool:
        """Write an audio frame to Asterisk via AudioSocket.

        Args:
            frame: The output audio frame to write.

        Returns:
            True if the audio frame was written successfully, False otherwise.
        """
        if not self._writer:
            return False

        try:
            # Resample from pipeline rate (16kHz) to Asterisk rate (8kHz)
            resampled_audio = resample_audio(
                frame.audio,
                self._params.pipeline_sample_rate,
                self._params.asterisk_sample_rate,
            )

            # Build AudioSocket packet
            packet = self._build_audio_packet(resampled_audio)

            # Send to Asterisk
            self._writer.write(packet)
            await self._writer.drain()

            return True

        except Exception as e:
            logger.error(f"Error writing audio to Asterisk: {e}")
            return False

    def _build_audio_packet(self, audio_data: bytes) -> bytes:
        """Build an AudioSocket audio packet.

        Args:
            audio_data: Raw audio bytes to send.

        Returns:
            Complete AudioSocket packet with header.
        """
        # Header: type (1 byte) + length (2 bytes big-endian)
        header = struct.pack(">BH", AUDIOSOCKET_TYPE_AUDIO, len(audio_data))
        return header + audio_data

    async def _send_terminate(self):
        """Send a terminate packet to Asterisk."""
        if not self._writer:
            return

        try:
            # Terminate packet has no payload
            packet = struct.pack(">BH", AUDIOSOCKET_TYPE_TERMINATE, 0)
            self._writer.write(packet)
            await self._writer.drain()
        except Exception as e:
            logger.debug(f"Error sending terminate packet: {e}")


class AudioSocketTransport(BaseTransport):
    """AudioSocket transport for bidirectional audio with Asterisk.

    Provides a complete TCP AudioSocket server implementation with separate input
    and output transports for real-time audio streaming with Asterisk PBX.

    Usage:
        transport = AudioSocketTransport(
            AudioSocketParams(host="0.0.0.0", port=9001)
        )

        pipeline = Pipeline([
            transport.input(),
            stt,
            llm,
            tts,
            transport.output(),
        ])
    """

    def __init__(
        self,
        params: AudioSocketParams,
        input_name: Optional[str] = None,
        output_name: Optional[str] = None,
    ):
        """Initialize the AudioSocket transport.

        Args:
            params: AudioSocket configuration parameters.
            input_name: Optional name for the input processor.
            output_name: Optional name for the output processor.
        """
        super().__init__(input_name=input_name, output_name=output_name)
        self._params = params

        self._callbacks = AudioSocketCallbacks(
            on_client_connected=self._on_client_connected,
            on_client_disconnected=self._on_client_disconnected,
        )
        self._input: Optional[AudioSocketInputTransport] = None
        self._output: Optional[AudioSocketOutputTransport] = None

        # Register event handlers
        self._register_event_handler("on_client_connected")
        self._register_event_handler("on_client_disconnected")

    def input(self) -> AudioSocketInputTransport:
        """Get the input transport for receiving audio from Asterisk.

        Returns:
            The AudioSocket input transport instance.
        """
        if not self._input:
            self._input = AudioSocketInputTransport(
                self, self._params, self._callbacks, name=self._input_name
            )
        return self._input

    def output(self) -> AudioSocketOutputTransport:
        """Get the output transport for sending audio to Asterisk.

        Returns:
            The AudioSocket output transport instance.
        """
        if not self._output:
            self._output = AudioSocketOutputTransport(
                self, self._params, name=self._output_name
            )
        return self._output

    async def _on_client_connected(self, call_uuid: str):
        """Handle Asterisk connection events."""
        logger.info(f"Asterisk call connected: {call_uuid}")

        # Share the writer with output transport
        if self._output and self._input and self._input._writer:
            self._output.set_writer(self._input._writer)

        await self._call_event_handler("on_client_connected", call_uuid)

    async def _on_client_disconnected(self, call_uuid: str):
        """Handle Asterisk disconnection events."""
        logger.info(f"Asterisk call disconnected: {call_uuid}")

        if self._output:
            self._output.set_writer(None)

        await self._call_event_handler("on_client_disconnected", call_uuid)
