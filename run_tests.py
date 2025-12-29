#!/usr/bin/env python3
"""
Test Runner - Un seul terminal suffit!

Usage:
    python run_tests.py          # Tous les tests
    python run_tests.py stt      # Test STT seul
    python run_tests.py llm      # Test LLM seul
    python run_tests.py tts      # Test TTS seul
    python run_tests.py full     # Test complet E2E
    python run_tests.py --play   # Joue les audios automatiquement
"""

import argparse
import os
import subprocess
import sys


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def run_test(script: str, args: list = None):
    """Run a test script."""
    cmd = [sys.executable, script]
    if args:
        cmd.extend(args)
    
    result = subprocess.run(
        cmd, 
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Tests - Medical Voice Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
    python run_tests.py          # Test rapide de tous les modules
    python run_tests.py stt      # Test Whisper STT
    python run_tests.py llm      # Test Ollama LLM
    python run_tests.py tts      # Test Coqui TTS
    python run_tests.py full     # Test complet end-to-end
    python run_tests.py --play   # Joue les audios automatiquement
        """
    )
    parser.add_argument("module", nargs="?", default="all",
                       choices=["all", "stt", "llm", "tts", "full"])
    parser.add_argument("--play", action="store_true",
                       help="Joue les fichiers audio automatiquement")
    
    args = parser.parse_args()
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    extra_args = ["--play"] if args.play else []
    results = {}
    
    if args.module == "stt" or args.module == "all":
        print_header("🎙️ Test STT (Whisper)")
        results["stt"] = run_test("tests/test_stt.py")
    
    if args.module == "llm" or args.module == "all":
        print_header("🧠 Test LLM (Ollama)")
        results["llm"] = run_test("tests/test_llm.py")
    
    if args.module == "tts" or args.module == "all":
        print_header("🔊 Test TTS (Coqui)")
        results["tts"] = run_test("tests/test_tts.py", extra_args if args.play else None)
    
    if args.module == "full":
        print_header("🚀 Test Complet E2E")
        results["full"] = run_test("tests/test_full.py", extra_args)
    
    # Summary
    if results:
        print_header("📊 Résumé")
        for module, success in results.items():
            status = "✅ OK" if success else "❌ ÉCHEC"
            print(f"   {module.upper()}: {status}")
        
        all_passed = all(results.values())
        print(f"\n   {'='*30}")
        print(f"   {'✅ TOUS LES TESTS OK' if all_passed else '❌ ÉCHECS DÉTECTÉS'}")


if __name__ == "__main__":
    main()
