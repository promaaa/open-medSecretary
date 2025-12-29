#!/usr/bin/env python3
"""
Test Runner - Run all tests or specific modules

Usage:
    python run_tests.py              # Run all tests
    python run_tests.py stt          # Test STT only
    python run_tests.py llm          # Test LLM only
    python run_tests.py tts          # Test TTS only
    python run_tests.py full         # Full system test
    python run_tests.py benchmark    # Benchmark all modules
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
    cmd = ["python", script]
    if args:
        cmd.extend(args)
    
    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Run tests for Medical Voice Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_tests.py              # Quick test of all modules
    python run_tests.py stt          # Test Whisper STT
    python run_tests.py llm          # Test Ollama LLM
    python run_tests.py tts          # Test Coqui/Piper TTS
    python run_tests.py full         # Full end-to-end test
    python run_tests.py benchmark    # Benchmark all modules for optimization
        """
    )
    parser.add_argument("module", nargs="?", default="all",
                       choices=["all", "stt", "llm", "tts", "full", "benchmark"],
                       help="Module to test")
    
    args = parser.parse_args()
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    results = {}
    
    if args.module == "stt" or args.module == "all":
        print_header("🎙️ Testing STT (Whisper)")
        results["stt"] = run_test("tests/test_stt.py")
    
    if args.module == "llm" or args.module == "all":
        print_header("🧠 Testing LLM (Ollama)")
        results["llm"] = run_test("tests/test_llm.py")
    
    if args.module == "tts" or args.module == "all":
        print_header("🔊 Testing TTS (Coqui)")
        results["tts"] = run_test("tests/test_tts.py")
    
    if args.module == "full":
        print_header("🚀 Full System Test")
        results["full"] = run_test("tests/test_full.py")
    
    if args.module == "benchmark":
        print_header("🏃 Benchmarking All Modules")
        
        print("\n--- STT Benchmark ---")
        run_test("tests/test_stt.py", ["--benchmark"])
        
        print("\n--- LLM Benchmark ---")
        run_test("tests/test_llm.py", ["--benchmark"])
        
        print("\n--- TTS Benchmark ---")
        run_test("tests/test_tts.py", ["--benchmark"])
    
    # Summary
    if results:
        print_header("📊 Test Summary")
        for module, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {module.upper()}: {status}")
        
        all_passed = all(results.values())
        print(f"\n   {'='*30}")
        print(f"   Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")


if __name__ == "__main__":
    main()
