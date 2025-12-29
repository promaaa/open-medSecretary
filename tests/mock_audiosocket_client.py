#!/usr/bin/env python3
#
# Copyright (c) 2024-2025
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""
Mock AudioSocket Client for Testing

Simulates an Asterisk AudioSocket connection for testing the medical
voice assistant without a real PBX.

Usage:
    python tests/mock_audiosocket_client.py
    python tests/mock_audiosocket_client.py --audio-file test.wav
    python tests/mock_audiosocket_client.py --host 127.0.0.1 --port 9001
"""

import argparse
import asyncio
import struct
import sys
import uuid
import wave
from pathlib import Path

# AudioSocket packet types
TYPE_TERMINATE = 0x00
TYPE_UUID = 0x01
TYPE_AUDIO = 0x10


def build_packet(packet_type: int, payload: bytes) -> bytes:
    """Build an AudioSocket packet."""
    header = struct.pack(">BH", packet_type, len(payload))
    return header + payload


def parse_packet(data: bytes) -> tuple:
    """Parse an AudioSocket packet header."""
    if len(data) < 3:
        return None, 0
    packet_type = data[0]
    payload_length = struct.unpack(">H", data[1:3])[0]
    return packet_type, payload_length


async def receive_audio(reader: asyncio.StreamReader, output_file: str):
    """Receive and save audio from the server."""
    audio_data = []
    
    print("📥 Receiving audio from server...")
    
    try:
        while not reader.at_eof():
            # Read header
            header = await asyncio.wait_for(reader.readexactly(3), timeout=30.0)
            packet_type, payload_length = parse_packet(header)
            
            # Read payload
            if payload_length > 0:
                payload = await reader.readexactly(payload_length)
            else:
                payload = b""
            
            if packet_type == TYPE_TERMINATE:
                print("📴 Received TERMINATE packet")
                break
            elif packet_type == TYPE_AUDIO:
                audio_data.append(payload)
                print(f"📥 Received {len(payload)} bytes of audio")
            
    except asyncio.TimeoutError:
        print("⏱️ Timeout waiting for response")
    except asyncio.IncompleteReadError:
        print("📴 Connection closed by server")
    except Exception as e:
        print(f"❌ Error receiving: {e}")
    
    # Save received audio
    if audio_data:
        all_audio = b"".join(audio_data)
        with wave.open(output_file, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)  # AudioSocket uses 8kHz
            wf.writeframes(all_audio)
        print(f"💾 Saved {len(all_audio)} bytes to {output_file}")


async def main(host: str, port: int, audio_file: str = None, output_file: str = "response.wav"):
    """Run mock AudioSocket client."""
    
    print(f"🔌 Connecting to {host}:{port}...")
    
    try:
        reader, writer = await asyncio.open_connection(host, port)
        print("✅ Connected!")
        
        # Send UUID packet
        call_uuid = str(uuid.uuid4())
        uuid_packet = build_packet(TYPE_UUID, call_uuid.encode("utf-8"))
        writer.write(uuid_packet)
        await writer.drain()
        print(f"📤 Sent UUID: {call_uuid}")
        
        # Send audio if file provided
        if audio_file and Path(audio_file).exists():
            print(f"📤 Sending audio from {audio_file}...")
            
            with wave.open(audio_file, "rb") as wf:
                # Read all audio
                audio_data = wf.readframes(wf.getnframes())
                
                # Send in chunks (320 bytes = 20ms at 8kHz mono 16-bit)
                chunk_size = 320
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i : i + chunk_size]
                    packet = build_packet(TYPE_AUDIO, chunk)
                    writer.write(packet)
                    await writer.drain()
                    # Simulate real-time: 20ms per chunk
                    await asyncio.sleep(0.02)
                
                print(f"📤 Sent {len(audio_data)} bytes of audio")
        else:
            # Generate synthetic audio (silence with some noise)
            print("📤 Sending 3 seconds of test silence...")
            sample_rate = 8000
            duration_sec = 3
            num_samples = sample_rate * duration_sec
            
            # Generate mostly silence
            import random
            audio_data = bytes([
                (random.randint(-100, 100) + 128) % 256 
                for _ in range(num_samples * 2)
            ])
            
            chunk_size = 320
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i : i + chunk_size]
                packet = build_packet(TYPE_AUDIO, chunk)
                writer.write(packet)
                await writer.drain()
                await asyncio.sleep(0.02)
            
            print(f"📤 Sent {len(audio_data)} bytes of test audio")
        
        # Receive response
        await receive_audio(reader, output_file)
        
        # Send terminate
        terminate_packet = build_packet(TYPE_TERMINATE, b"")
        writer.write(terminate_packet)
        await writer.drain()
        print("📤 Sent TERMINATE")
        
        # Close connection
        writer.close()
        await writer.wait_closed()
        print("✅ Connection closed")
        
    except ConnectionRefusedError:
        print(f"❌ Connection refused. Is the server running on {host}:{port}?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock AudioSocket Client")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=9001, help="Server port")
    parser.add_argument("--audio-file", help="WAV file to send (8kHz mono)")
    parser.add_argument("--output-file", default="response.wav", help="Output WAV file")
    
    args = parser.parse_args()
    
    asyncio.run(main(args.host, args.port, args.audio_file, args.output_file))
