#!/usr/bin/env python3
"""
Full System Test - End-to-End Pipeline

Tests the complete voice assistant pipeline with all components.

Usage:
    python tests/test_full.py
    python tests/test_full.py --audio /path/to/audio.wav
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_service(name: str, url: str) -> bool:
    """Check if a service is running."""
    import urllib.request
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except:
        return False


def create_test_audio():
    """Create a test audio file with speech."""
    from TTS.api import TTS
    import numpy as np
    import wave
    from scipy import signal
    
    print("🎤 Creating test audio...")
    tts = TTS('tts_models/fr/css10/vits')
    wav = tts.tts("Bonjour, je voudrais prendre un rendez-vous pour demain matin s'il vous plaît.")
    
    # Convert to 8kHz (Asterisk format)
    audio_int16 = (np.array(wav) * 32767).astype(np.int16)
    resampled = signal.resample(audio_int16, int(len(audio_int16) * 8000 / 22050))
    resampled_int16 = resampled.astype(np.int16)
    
    audio_path = "/tmp/test_full_speech.wav"
    with wave.open(audio_path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(resampled_int16.tobytes())
    
    print(f"✅ Created: {audio_path}")
    return audio_path


async def test_full_pipeline(audio_path: str = None):
    """Test the full voice assistant pipeline."""
    
    print(f"\n{'='*60}")
    print(f"🚀 Full System Test")
    print(f"{'='*60}\n")
    
    # Check prerequisites
    print("📋 Checking prerequisites...\n")
    
    services = [
        ("Ollama", "http://localhost:11434/api/tags"),
        ("Coqui TTS", "http://localhost:5555/health"),
    ]
    
    missing = []
    for name, url in services:
        if check_service(name, url):
            print(f"   ✅ {name} is running")
        else:
            print(f"   ❌ {name} is NOT running")
            missing.append(name)
    
    if missing:
        print(f"\n⚠️ Missing services: {', '.join(missing)}")
        print("\nStart them with:")
        if "Ollama" in missing:
            print("   ollama run llama3:8b")
        if "Coqui TTS" in missing:
            print("   python coqui_server.py")
        return False
    
    # Create test audio if needed
    if not audio_path:
        audio_path = create_test_audio()
    
    # Start main.py in background
    print("\n🚀 Starting voice assistant...")
    main_process = subprocess.Popen(
        ["python", "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    
    # Wait for server to start
    await asyncio.sleep(5)
    
    # Check if AudioSocket is ready
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", 9001))
        sock.close()
        print("   ✅ AudioSocket server ready on port 9001")
    except:
        print("   ❌ AudioSocket server failed to start")
        main_process.terminate()
        return False
    
    # Run test client
    print("\n📞 Running test call...")
    start_time = time.time()
    
    result = subprocess.run(
        ["python", "tests/mock_audiosocket_client.py", "--audio-file", audio_path],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        timeout=60
    )
    
    total_time = time.time() - start_time
    
    # Stop main.py
    main_process.terminate()
    main_process.wait()
    
    # Parse results
    output = result.stdout + result.stderr
    
    # Check for success indicators
    connected = "Connected!" in output
    audio_received = "Received" in output and "bytes of audio" in output
    saved = "Saved" in output and "bytes to response.wav" in output
    
    print(f"\n{'='*60}")
    print(f"📊 Test Results")
    print(f"{'='*60}")
    print(f"   Connection: {'✅ Success' if connected else '❌ Failed'}")
    print(f"   Audio Received: {'✅ Yes' if audio_received else '❌ No'}")
    print(f"   Response Saved: {'✅ Yes' if saved else '❌ No'}")
    print(f"   Total Time: {total_time:.2f}s")
    print(f"{'='*60}")
    
    if saved:
        response_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "response.wav"
        )
        print(f"\n🎧 Listen to response: afplay {response_path}")
    
    return connected and audio_received


def main():
    parser = argparse.ArgumentParser(description="Full system test")
    parser.add_argument("--audio", default=None,
                       help="Path to audio file to use")
    
    args = parser.parse_args()
    
    success = asyncio.run(test_full_pipeline(audio_path=args.audio))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
