#!/usr/bin/env python3
"""
Test STT (Speech-to-Text) - Whisper

Tests the Whisper transcription with different models and settings.
Use this to find the optimal model for your hardware.

Usage:
    python tests/test_stt.py
    python tests/test_stt.py --model medium
    python tests/test_stt.py --audio /path/to/audio.wav
"""

import argparse
import asyncio
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_test_audio():
    """Create a test audio file with TTS."""
    try:
        from TTS.api import TTS
        import numpy as np
        import wave
        from scipy import signal
        
        print("🎤 Creating test audio with TTS...")
        tts = TTS('tts_models/fr/css10/vits')
        wav = tts.tts("Bonjour, je voudrais prendre un rendez-vous pour demain matin.")
        
        # Convert to 16kHz for Whisper
        audio_int16 = (np.array(wav) * 32767).astype(np.int16)
        resampled = signal.resample(audio_int16, int(len(audio_int16) * 16000 / 22050))
        resampled_int16 = resampled.astype(np.int16)
        
        audio_path = "/tmp/test_stt_audio.wav"
        with wave.open(audio_path, 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(resampled_int16.tobytes())
        
        return audio_path, resampled_int16.tobytes()
    except ImportError:
        print("⚠️ TTS not available, using silence for test")
        import numpy as np
        silence = np.zeros(16000 * 3, dtype=np.int16)  # 3 seconds
        return None, silence.tobytes()


async def test_whisper(model: str = "small", device: str = "auto", audio_path: str = None):
    """Test Whisper STT with specified settings."""
    from pipecat.services.whisper.stt import WhisperSTTService
    from pipecat.transcriptions.language import Language
    from pipecat.frames.frames import AudioRawFrame
    
    print(f"\n{'='*60}")
    print(f"🎙️ Testing Whisper STT")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Device: {device}")
    print(f"Language: French")
    print()
    
    # Load model
    print("⏳ Loading model...")
    start = time.time()
    
    stt = WhisperSTTService(
        model=model,
        device=device,
        compute_type="default",
        language=Language.FR,
        no_speech_prob=0.4,
    )
    
    load_time = time.time() - start
    print(f"✅ Model loaded in {load_time:.2f}s")
    
    # Get test audio
    if audio_path:
        import wave
        with wave.open(audio_path, 'rb') as f:
            audio_bytes = f.readframes(f.getnframes())
            sample_rate = f.getframerate()
        print(f"📁 Using audio file: {audio_path}")
    else:
        audio_path, audio_bytes = create_test_audio()
        sample_rate = 16000
    
    # Transcribe
    print("\n⏳ Transcribing...")
    start = time.time()
    
    async for frame in stt.run_stt(audio_bytes):
        if hasattr(frame, 'text'):
            transcribe_time = time.time() - start
            print(f"\n✅ Transcription ({transcribe_time:.2f}s):")
            print(f"   \"{frame.text}\"")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"📊 Results for model '{model}':")
    print(f"   Load time: {load_time:.2f}s")
    print(f"   Transcribe time: {transcribe_time:.2f}s")
    print(f"{'='*60}")
    
    return {"model": model, "load_time": load_time, "transcribe_time": transcribe_time}


async def benchmark_models():
    """Benchmark multiple Whisper models."""
    models = ["tiny", "base", "small"]
    results = []
    
    print("\n🏃 Benchmarking Whisper models...")
    print("This will test: tiny, base, small\n")
    
    for model in models:
        try:
            result = await test_whisper(model=model)
            results.append(result)
        except Exception as e:
            print(f"❌ {model} failed: {e}")
    
    print("\n" + "="*60)
    print("📊 BENCHMARK RESULTS")
    print("="*60)
    print(f"{'Model':<10} {'Load Time':<12} {'Transcribe':<12}")
    print("-"*34)
    for r in results:
        print(f"{r['model']:<10} {r['load_time']:.2f}s{'':<6} {r['transcribe_time']:.2f}s")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Test Whisper STT")
    parser.add_argument("--model", default="small", 
                       choices=["tiny", "base", "small", "medium", "large-v3"],
                       help="Whisper model to use")
    parser.add_argument("--device", default="auto",
                       choices=["auto", "cpu", "cuda"],
                       help="Device to run on")
    parser.add_argument("--audio", default=None,
                       help="Path to audio file to transcribe")
    parser.add_argument("--benchmark", action="store_true",
                       help="Benchmark multiple models")
    
    args = parser.parse_args()
    
    if args.benchmark:
        asyncio.run(benchmark_models())
    else:
        asyncio.run(test_whisper(model=args.model, device=args.device, audio_path=args.audio))


if __name__ == "__main__":
    main()
