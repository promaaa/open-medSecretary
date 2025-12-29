#!/usr/bin/env python3
"""
Test Complet - Pipeline End-to-End

Simple test - lance tout automatiquement, un seul terminal!

Usage:
    python tests/test_full.py
    python tests/test_full.py --play  # Joue la réponse automatiquement
"""

import argparse
import atexit
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Track background processes for cleanup
_processes = []


def cleanup():
    """Kill all background processes."""
    for p in _processes:
        try:
            p.terminate()
            p.wait(timeout=2)
        except:
            try:
                p.kill()
            except:
                pass


atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))


def check_port(port: int) -> bool:
    """Check if a port is open."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect(("127.0.0.1", port))
        sock.close()
        return True
    except:
        return False


def wait_for_port(port: int, timeout: int = 30):
    """Wait for a port to become available."""
    start = time.time()
    while time.time() - start < timeout:
        if check_port(port):
            return True
        time.sleep(0.5)
    return False


def start_ollama():
    """Start Ollama if not running."""
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        print("   ✅ Ollama déjà actif")
        return True
    except:
        pass
    
    print("   ⏳ Démarrage Ollama...")
    p = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    _processes.append(p)
    time.sleep(3)
    
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
        print("   ✅ Ollama démarré")
        return True
    except:
        print("   ❌ Échec Ollama")
        return False


def start_tts():
    """Start Coqui TTS server."""
    if check_port(5555):
        print("   ✅ TTS déjà actif")
        return True
    
    print("   ⏳ Démarrage TTS (peut prendre 10-20s)...")
    
    p = subprocess.Popen(
        [sys.executable, "coqui_server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    _processes.append(p)
    
    if wait_for_port(5555, timeout=30):
        print("   ✅ TTS démarré")
        return True
    else:
        print("   ❌ Échec TTS")
        return False


def start_main():
    """Start main voice assistant."""
    if check_port(9001):
        print("   ✅ Assistant déjà actif")
        return True
    
    print("   ⏳ Démarrage assistant...")
    
    p = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    _processes.append(p)
    
    if wait_for_port(9001, timeout=15):
        print("   ✅ Assistant démarré")
        return True
    else:
        print("   ❌ Échec assistant")
        return False


def create_test_audio():
    """Create test audio with TTS."""
    from TTS.api import TTS
    import numpy as np
    import wave
    from scipy import signal
    
    print("\n⏳ Création audio de test...")
    tts = TTS('tts_models/fr/css10/vits')
    wav = tts.tts("Bonjour, je voudrais prendre un rendez-vous pour demain matin.")
    
    audio_int16 = (np.array(wav) * 32767).astype(np.int16)
    resampled = signal.resample(audio_int16, int(len(audio_int16) * 8000 / 22050))
    resampled_int16 = resampled.astype(np.int16)
    
    audio_path = "/tmp/test_speech.wav"
    with wave.open(audio_path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(resampled_int16.tobytes())
    
    print(f"✅ Audio créé: {audio_path}")
    return audio_path


def test_full(play: bool = False):
    """Run complete end-to-end test."""
    
    print(f"\n{'='*60}")
    print(f"🚀 Test Complet - Pipeline E2E")
    print(f"{'='*60}")
    print(f"Ce test lance automatiquement tous les services.")
    print()
    
    # Start all services
    print("📋 Démarrage des services...\n")
    
    if not start_ollama():
        return False
    
    if not start_tts():
        return False
    
    if not start_main():
        return False
    
    # Create test audio
    audio_path = create_test_audio()
    
    # Run test client
    print("\n📞 Exécution du test...")
    start_time = time.time()
    
    result = subprocess.run(
        [sys.executable, "tests/mock_audiosocket_client.py", "--audio-file", audio_path],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        timeout=90
    )
    
    total_time = time.time() - start_time
    output = result.stdout + result.stderr
    
    # Parse results
    connected = "Connected!" in output
    received = "Received" in output and "bytes of audio" in output
    saved = "Saved" in output
    
    # Get response size
    response_size = 0
    if saved:
        for line in output.split("\n"):
            if "Saved" in line and "bytes" in line:
                try:
                    response_size = int(line.split()[1])
                except:
                    pass
    
    print(f"\n{'='*60}")
    print(f"📊 Résultats:")
    print(f"{'='*60}")
    print(f"   Connexion: {'✅' if connected else '❌'}")
    print(f"   Audio reçu: {'✅' if received else '❌'}")
    print(f"   Réponse: {response_size} bytes")
    print(f"   Temps total: {total_time:.1f}s")
    print(f"{'='*60}")
    
    response_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "response.wav"
    )
    
    if os.path.exists(response_path):
        if play:
            print(f"\n🎧 Lecture de la réponse...")
            subprocess.run(["afplay", response_path])
        else:
            print(f"\n🎧 Pour écouter: afplay {response_path}")
    
    success = connected and received and response_size > 0
    print(f"\n{'✅ TEST RÉUSSI!' if success else '❌ TEST ÉCHOUÉ'}")
    
    return success


def main():
    parser = argparse.ArgumentParser(description="Test complet E2E")
    parser.add_argument("--play", action="store_true", help="Joue la réponse automatiquement")
    args = parser.parse_args()
    
    success = test_full(play=args.play)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
