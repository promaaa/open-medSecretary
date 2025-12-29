#!/usr/bin/env python3
"""
Test STT (Speech-to-Text) - Whisper

Simple test - just run it, no other terminals needed!

Usage:
    python tests/test_stt.py
    python tests/test_stt.py --model medium
    python tests/test_stt.py --benchmark
"""

import argparse
import asyncio
import os
import sys
import time
import wave
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_audio_simple():
    """Create simple test audio without TTS dependency."""
    import numpy as np
    
    # Generate a simple tone (more reliable than TTS for testing)
    sample_rate = 16000
    duration = 2  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Mix of frequencies to simulate speech-like audio
    audio = np.sin(2 * np.pi * 440 * t) * 0.3
    audio += np.sin(2 * np.pi * 880 * t) * 0.2
    audio_int16 = (audio * 32767).astype(np.int16)
    
    return audio_int16.tobytes(), sample_rate


def test_whisper(model: str = "small", device: str = "auto"):
    """Test Whisper STT - standalone, no other services needed."""
    
    print(f"\n{'='*60}")
    print(f"🎙️ Test STT - Whisper")
    print(f"{'='*60}")
    print(f"Modèle: {model}")
    print(f"Device: {device}")
    print()
    
    # Import
    print("⏳ Chargement du modèle...")
    start = time.time()
    
    from pipecat.services.whisper.stt import WhisperSTTService
    from pipecat.transcriptions.language import Language
    
    stt = WhisperSTTService(
        model=model,
        device=device,
        compute_type="default",
        language=Language.FR,
        no_speech_prob=0.4,
    )
    
    load_time = time.time() - start
    print(f"✅ Modèle chargé en {load_time:.2f}s")
    
    # Create test audio
    print("\n⏳ Création audio de test...")
    audio_bytes, sample_rate = create_test_audio_simple()
    print(f"✅ Audio créé ({len(audio_bytes)} bytes)")
    
    # Transcribe
    print("\n⏳ Transcription...")
    start = time.time()
    
    async def run_stt():
        results = []
        async for frame in stt.run_stt(audio_bytes):
            if hasattr(frame, 'text') and frame.text:
                results.append(frame.text)
        return results
    
    results = asyncio.run(run_stt())
    transcribe_time = time.time() - start
    
    if results:
        print(f"✅ Résultat: \"{results[0]}\"")
    else:
        print("ℹ️ Pas de parole détectée (normal avec audio de test)")
    
    print(f"\n{'='*60}")
    print(f"📊 Résultats '{model}':")
    print(f"   Chargement: {load_time:.2f}s")
    print(f"   Transcription: {transcribe_time:.2f}s")
    print(f"{'='*60}")
    
    return {"model": model, "load_time": load_time, "transcribe_time": transcribe_time}


def benchmark():
    """Benchmark plusieurs modèles."""
    models = ["tiny", "base", "small"]
    results = []
    
    print("\n🏃 Benchmark des modèles Whisper...")
    
    for model in models:
        try:
            r = test_whisper(model=model)
            results.append(r)
        except Exception as e:
            print(f"❌ {model}: {e}")
    
    print(f"\n{'='*60}")
    print("📊 RÉSUMÉ")
    print(f"{'='*60}")
    print(f"{'Modèle':<10} {'Chargement':<12} {'Transcription'}")
    print("-"*40)
    for r in results:
        print(f"{r['model']:<10} {r['load_time']:.2f}s{'':<6} {r['transcribe_time']:.2f}s")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Test Whisper STT")
    parser.add_argument("--model", default="small", 
                       choices=["tiny", "base", "small", "medium", "large-v3"])
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args()
    
    if args.benchmark:
        benchmark()
    else:
        test_whisper(model=args.model, device=args.device)


if __name__ == "__main__":
    main()
