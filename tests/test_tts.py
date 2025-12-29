#!/usr/bin/env python3
"""
Test TTS (Text-to-Speech) - Coqui / Piper

Tests TTS engines with different models and voices.
Use this to find the optimal TTS for your hardware.

Usage:
    python tests/test_tts.py
    python tests/test_tts.py --engine coqui --model tts_models/fr/css10/vits
    python tests/test_tts.py --engine piper
    python tests/test_tts.py --text "Bonjour, comment allez-vous?"
"""

import argparse
import asyncio
import io
import os
import sys
import time
import wave

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_coqui(model: str, text: str) -> dict:
    """Test Coqui TTS."""
    from TTS.api import TTS
    import numpy as np
    
    print(f"\n{'='*60}")
    print(f"🔊 Testing Coqui TTS")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Text: {text}")
    print()
    
    # Load model
    print("⏳ Loading model...")
    start = time.time()
    tts = TTS(model)
    load_time = time.time() - start
    print(f"✅ Model loaded in {load_time:.2f}s")
    
    # Synthesize
    print("\n⏳ Synthesizing...")
    start = time.time()
    wav = tts.tts(text)
    synth_time = time.time() - start
    
    # Convert to WAV
    audio_int16 = (np.array(wav) * 32767).astype(np.int16)
    sample_rate = tts.synthesizer.output_sample_rate
    
    # Calculate audio duration
    duration = len(audio_int16) / sample_rate
    
    # Save to file
    output_path = "/tmp/test_tts_coqui.wav"
    with wave.open(output_path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(audio_int16.tobytes())
    
    print(f"✅ Synthesized in {synth_time:.2f}s")
    print(f"📁 Saved to: {output_path}")
    
    # Print summary
    rtf = synth_time / duration  # Real-time factor
    print(f"\n{'='*60}")
    print(f"📊 Results for Coqui '{model}':")
    print(f"   Load time: {load_time:.2f}s")
    print(f"   Synthesis time: {synth_time:.2f}s")
    print(f"   Audio duration: {duration:.2f}s")
    print(f"   Real-time factor: {rtf:.2f}x (lower is better)")
    print(f"   Sample rate: {sample_rate}Hz")
    print(f"{'='*60}")
    
    print(f"\n🎧 Listen with: afplay {output_path}")
    
    return {
        "engine": "coqui",
        "model": model,
        "load_time": load_time,
        "synth_time": synth_time,
        "duration": duration,
        "rtf": rtf
    }


def test_piper(voice: str, text: str) -> dict:
    """Test Piper TTS."""
    try:
        from piper import PiperVoice
    except ImportError:
        print("❌ Piper not installed. Run: pip install piper-tts")
        return None
    
    print(f"\n{'='*60}")
    print(f"🔊 Testing Piper TTS")
    print(f"{'='*60}")
    print(f"Voice: {voice}")
    print(f"Text: {text}")
    print()
    
    # Find voice model
    voice_path = os.path.expanduser(f"~/.local/share/piper_voices/{voice}/{voice}.onnx")
    if not os.path.exists(voice_path):
        print(f"❌ Voice not found: {voice_path}")
        print("   Download with the piper_server.py")
        return None
    
    # Load model
    print("⏳ Loading model...")
    start = time.time()
    piper_voice = PiperVoice.load(voice_path)
    load_time = time.time() - start
    print(f"✅ Model loaded in {load_time:.2f}s")
    
    # Synthesize
    print("\n⏳ Synthesizing...")
    start = time.time()
    
    audio_data = b''
    sample_rate = 22050
    for chunk in piper_voice.synthesize(text):
        audio_data += chunk.audio_int16_bytes
        sample_rate = chunk.sample_rate
    
    synth_time = time.time() - start
    
    # Calculate audio duration
    duration = len(audio_data) / 2 / sample_rate  # 2 bytes per sample
    
    # Save to file
    output_path = "/tmp/test_tts_piper.wav"
    with wave.open(output_path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(audio_data)
    
    print(f"✅ Synthesized in {synth_time:.2f}s")
    print(f"📁 Saved to: {output_path}")
    
    # Print summary
    rtf = synth_time / duration
    print(f"\n{'='*60}")
    print(f"📊 Results for Piper '{voice}':")
    print(f"   Load time: {load_time:.2f}s")
    print(f"   Synthesis time: {synth_time:.2f}s")
    print(f"   Audio duration: {duration:.2f}s")
    print(f"   Real-time factor: {rtf:.2f}x (lower is better)")
    print(f"   Sample rate: {sample_rate}Hz")
    print(f"{'='*60}")
    
    print(f"\n🎧 Listen with: afplay {output_path}")
    
    return {
        "engine": "piper",
        "model": voice,
        "load_time": load_time,
        "synth_time": synth_time,
        "duration": duration,
        "rtf": rtf
    }


def benchmark_tts():
    """Benchmark multiple TTS engines and models."""
    text = "Bonjour, cabinet médical, comment puis-je vous aider?"
    results = []
    
    print("\n🏃 Benchmarking TTS engines...")
    
    # Test Coqui models
    coqui_models = [
        "tts_models/fr/css10/vits",
        "tts_models/fr/mai/tacotron2-DDC",
    ]
    
    for model in coqui_models:
        try:
            result = test_coqui(model=model, text=text)
            if result:
                results.append(result)
        except Exception as e:
            print(f"❌ Coqui {model} failed: {e}")
    
    # Test Piper
    try:
        result = test_piper(voice="fr_FR-siwis-medium", text=text)
        if result:
            results.append(result)
    except Exception as e:
        print(f"❌ Piper failed: {e}")
    
    if results:
        print("\n" + "="*70)
        print("📊 BENCHMARK RESULTS")
        print("="*70)
        print(f"{'Engine':<8} {'Model':<30} {'RTF':<8} {'Synth':<8}")
        print("-"*54)
        for r in results:
            model_short = r['model'][-28:] if len(r['model']) > 28 else r['model']
            print(f"{r['engine']:<8} {model_short:<30} {r['rtf']:.2f}x{'':<4} {r['synth_time']:.2f}s")
        print("="*70)
        print("Note: RTF = Real-Time Factor (lower is better, <1 = faster than real-time)")


def main():
    parser = argparse.ArgumentParser(description="Test TTS engines")
    parser.add_argument("--engine", default="coqui",
                       choices=["coqui", "piper"],
                       help="TTS engine to use")
    parser.add_argument("--model", default="tts_models/fr/css10/vits",
                       help="Model/voice to use")
    parser.add_argument("--text", default="Bonjour, cabinet médical, comment puis-je vous aider?",
                       help="Text to synthesize")
    parser.add_argument("--benchmark", action="store_true",
                       help="Benchmark multiple TTS engines")
    
    args = parser.parse_args()
    
    if args.benchmark:
        benchmark_tts()
    elif args.engine == "coqui":
        test_coqui(model=args.model, text=args.text)
    else:
        test_piper(voice=args.model, text=args.text)


if __name__ == "__main__":
    main()
