#!/usr/bin/env python3
"""
Test TTS (Text-to-Speech) - Coqui

Simple test - just run it, no server needed!

Usage:
    python tests/test_tts.py
    python tests/test_tts.py --text "Bonjour"
    python tests/test_tts.py --play  # Joue l'audio automatiquement
"""

import argparse
import os
import subprocess
import sys
import time
import wave

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_tts(text: str = None, play: bool = False):
    """Test Coqui TTS - standalone, no server needed."""
    
    print(f"\n{'='*60}")
    print(f"🔊 Test TTS - Coqui VITS")
    print(f"{'='*60}")
    
    if not text:
        text = "Bonjour, cabinet médical, comment puis-je vous aider?"
    
    print(f"Texte: {text}")
    print()
    
    # Import and load
    print("⏳ Chargement du modèle...")
    start = time.time()
    
    from TTS.api import TTS
    import numpy as np
    
    model = "tts_models/fr/css10/vits"
    tts = TTS(model)
    
    load_time = time.time() - start
    print(f"✅ Modèle chargé en {load_time:.2f}s")
    
    # Synthesize
    print("\n⏳ Synthèse vocale...")
    start = time.time()
    
    wav = tts.tts(text)
    
    synth_time = time.time() - start
    
    # Convert and save
    audio_int16 = (np.array(wav) * 32767).astype(np.int16)
    sample_rate = tts.synthesizer.output_sample_rate
    duration = len(audio_int16) / sample_rate
    
    output_path = "/tmp/test_tts.wav"
    with wave.open(output_path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(audio_int16.tobytes())
    
    rtf = synth_time / duration  # Real-time factor
    
    print(f"✅ Synthèse terminée en {synth_time:.2f}s")
    print(f"📁 Fichier: {output_path}")
    
    print(f"\n{'='*60}")
    print(f"📊 Résultats:")
    print(f"   Chargement: {load_time:.2f}s")
    print(f"   Synthèse: {synth_time:.2f}s")
    print(f"   Durée audio: {duration:.2f}s")
    print(f"   RTF: {rtf:.2f}x {'(temps réel)' if rtf < 1 else '(plus lent)'}")
    print(f"{'='*60}")
    
    if play:
        print(f"\n🎧 Lecture...")
        subprocess.run(["afplay", output_path])
    else:
        print(f"\n🎧 Pour écouter: afplay {output_path}")
    
    return {"load_time": load_time, "synth_time": synth_time, "rtf": rtf}


def main():
    parser = argparse.ArgumentParser(description="Test Coqui TTS")
    parser.add_argument("--text", default=None)
    parser.add_argument("--play", action="store_true", help="Joue l'audio automatiquement")
    args = parser.parse_args()
    
    test_tts(text=args.text, play=args.play)


if __name__ == "__main__":
    main()
