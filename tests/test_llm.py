#!/usr/bin/env python3
"""
Test LLM (Language Model) - Ollama

Tests the Ollama LLM with different models and prompts.
Use this to find the optimal model for your hardware.

Usage:
    python tests/test_llm.py
    python tests/test_llm.py --model mistral
    python tests/test_llm.py --prompt "Je voudrais un rendez-vous"
"""

import argparse
import asyncio
import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_ollama(model: str = "llama3:8b", prompt: str = None):
    """Test Ollama LLM with specified settings."""
    import aiohttp
    
    print(f"\n{'='*60}")
    print(f"🧠 Testing Ollama LLM")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Base URL: http://localhost:11434")
    print()
    
    # Check if Ollama is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags") as resp:
                if resp.status != 200:
                    print("❌ Ollama is not running!")
                    print("   Start it with: ollama run llama3:8b")
                    return None
                data = await resp.json()
                available_models = [m["name"] for m in data.get("models", [])]
                print(f"✅ Ollama is running")
                print(f"   Available models: {', '.join(available_models)}")
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("   Start it with: ollama run llama3:8b")
        return None
    
    # Check if model is available
    if model not in available_models:
        print(f"\n⚠️ Model '{model}' not found. Pulling...")
        os.system(f"ollama pull {model}")
    
    # Import the service
    from services.medical_llm import MedicalLLMService
    from config.system_prompts import MEDICAL_SYSTEM_PROMPT
    
    # Create the service
    llm = MedicalLLMService(model=model, base_url="http://localhost:11434/v1")
    
    # Test prompt
    if not prompt:
        prompt = "Bonjour, je voudrais prendre un rendez-vous pour demain matin."
    
    print(f"\n📝 System prompt: {MEDICAL_SYSTEM_PROMPT[:100]}...")
    print(f"\n👤 User: {prompt}")
    print(f"\n🤖 Assistant: ", end="", flush=True)
    
    # Make request
    start = time.time()
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": MEDICAL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": True
        }
        
        full_response = ""
        async with session.post(
            "http://localhost:11434/v1/chat/completions",
            json=payload
        ) as resp:
            async for line in resp.content:
                if line:
                    try:
                        import json
                        data = json.loads(line.decode().replace("data: ", ""))
                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                print(content, end="", flush=True)
                                full_response += content
                    except:
                        pass
    
    response_time = time.time() - start
    
    print(f"\n\n{'='*60}")
    print(f"📊 Results for model '{model}':")
    print(f"   Response time: {response_time:.2f}s")
    print(f"   Response length: {len(full_response)} chars")
    print(f"{'='*60}")
    
    return {"model": model, "response_time": response_time, "response_length": len(full_response)}


async def benchmark_models():
    """Benchmark multiple Ollama models."""
    models = ["llama3:8b", "mistral", "gemma:7b"]
    results = []
    
    print("\n🏃 Benchmarking Ollama models...")
    print("This will test available models\n")
    
    for model in models:
        try:
            result = await test_ollama(model=model)
            if result:
                results.append(result)
        except Exception as e:
            print(f"❌ {model} failed: {e}")
    
    if results:
        print("\n" + "="*60)
        print("📊 BENCHMARK RESULTS")
        print("="*60)
        print(f"{'Model':<15} {'Response Time':<15} {'Length':<10}")
        print("-"*40)
        for r in results:
            print(f"{r['model']:<15} {r['response_time']:.2f}s{'':<9} {r['response_length']}")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Test Ollama LLM")
    parser.add_argument("--model", default="llama3:8b",
                       help="Ollama model to use")
    parser.add_argument("--prompt", default=None,
                       help="Custom prompt to test")
    parser.add_argument("--benchmark", action="store_true",
                       help="Benchmark multiple models")
    
    args = parser.parse_args()
    
    if args.benchmark:
        asyncio.run(benchmark_models())
    else:
        asyncio.run(test_ollama(model=args.model, prompt=args.prompt))


if __name__ == "__main__":
    main()
