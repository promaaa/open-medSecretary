#!/usr/bin/env python3
"""
Test LLM (Language Model) - Ollama

Simple test - just run it! Auto-starts Ollama if needed.

Usage:
    python tests/test_llm.py
    python tests/test_llm.py --model mistral
"""

import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_ollama():
    """Check if Ollama is running, start it if not."""
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except:
        return False


def start_ollama():
    """Start Ollama service."""
    print("⏳ Démarrage d'Ollama...")
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(3)
    return check_ollama()


def test_ollama(model: str = "llama3:8b", prompt: str = None):
    """Test Ollama LLM - auto-starts if needed."""
    
    print(f"\n{'='*60}")
    print(f"🧠 Test LLM - Ollama")
    print(f"{'='*60}")
    print(f"Modèle: {model}")
    print()
    
    # Check/start Ollama
    if not check_ollama():
        if not start_ollama():
            print("❌ Impossible de démarrer Ollama")
            print("   Installez-le avec: brew install ollama")
            return None
    
    print("✅ Ollama est prêt")
    
    # Check model
    import urllib.request
    import json
    
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags") as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
    except:
        models = []
    
    if model not in models:
        print(f"\n⏳ Téléchargement du modèle {model}...")
        subprocess.run(["ollama", "pull", model], capture_output=True)
    
    # Test prompt
    if not prompt:
        prompt = "Bonjour, je voudrais un rendez-vous demain."
    
    from config.system_prompts import MEDICAL_SYSTEM_PROMPT
    
    print(f"\n👤 User: {prompt}")
    print(f"🤖 Assistant: ", end="", flush=True)
    
    # Make request
    start = time.time()
    
    import urllib.request
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": MEDICAL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }).encode()
    
    req = urllib.request.Request(
        "http://localhost:11434/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        response = data["choices"][0]["message"]["content"]
    
    response_time = time.time() - start
    
    print(response)
    
    print(f"\n{'='*60}")
    print(f"📊 Résultats '{model}':")
    print(f"   Temps de réponse: {response_time:.2f}s")
    print(f"   Longueur: {len(response)} caractères")
    print(f"{'='*60}")
    
    return {"model": model, "response_time": response_time}


def main():
    parser = argparse.ArgumentParser(description="Test Ollama LLM")
    parser.add_argument("--model", default="llama3:8b")
    parser.add_argument("--prompt", default=None)
    args = parser.parse_args()
    
    test_ollama(model=args.model, prompt=args.prompt)


if __name__ == "__main__":
    main()
