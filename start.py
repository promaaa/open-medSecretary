#!/usr/bin/env python3
"""
Open Medical Secretary - Unified Launcher
One command to start everything!
"""

import os
import sys
import time
import signal
import asyncio
import subprocess
import webbrowser
import threading
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Configuration
WEB_PORT = 3000
OLLAMA_PORT = 11434
TTS_PORT = 5555
ASSISTANT_PORT = 9001

class OpenMedicalSecretary:
    def __init__(self):
        self.processes = []
        self.base_dir = Path(__file__).parent
        self.running = True
        
    def log(self, message, level="INFO"):
        colors = {
            "INFO": "\033[94m",
            "OK": "\033[92m",
            "WARN": "\033[93m",
            "ERROR": "\033[91m",
            "RESET": "\033[0m"
        }
        timestamp = time.strftime("%H:%M:%S")
        print(f"{colors.get(level, '')}{timestamp} [{level}] {message}{colors['RESET']}")

    def check_port(self, port):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def wait_for_port(self, port, timeout=30):
        start = time.time()
        while time.time() - start < timeout:
            if self.check_port(port):
                return True
            time.sleep(0.5)
        return False

    def start_ollama(self):
        """Start Ollama if not running."""
        if self.check_port(OLLAMA_PORT):
            self.log("Ollama déjà actif", "OK")
            return True
        
        self.log("Démarrage d'Ollama...")
        try:
            proc = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.processes.append(proc)
            if self.wait_for_port(OLLAMA_PORT, 15):
                self.log("Ollama démarré", "OK")
                return True
            else:
                self.log("Ollama timeout", "WARN")
                return False
        except FileNotFoundError:
            self.log("Ollama non installé! Exécutez ./install.sh", "ERROR")
            return False

    def start_tts(self):
        """Start Coqui TTS server."""
        if self.check_port(TTS_PORT):
            self.log("TTS déjà actif", "OK")
            return True
        
        self.log("Démarrage TTS (Coqui)...")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.base_dir)
        
        proc = subprocess.Popen(
            [sys.executable, str(self.base_dir / "backend" / "coqui_server.py")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
        self.processes.append(proc)
        
        if self.wait_for_port(TTS_PORT, 60):
            self.log("TTS démarré", "OK")
            return True
        else:
            self.log("TTS timeout (premier démarrage peut être long)", "WARN")
            return True  # Continue anyway

    def start_assistant(self):
        """Start the voice assistant."""
        if self.check_port(ASSISTANT_PORT):
            self.log("Assistant déjà actif", "OK")
            return True
        
        self.log("Démarrage Assistant IA...")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.base_dir)
        
        proc = subprocess.Popen(
            [sys.executable, str(self.base_dir / "backend" / "main.py")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
        self.processes.append(proc)
        
        if self.wait_for_port(ASSISTANT_PORT, 30):
            self.log("Assistant démarré", "OK")
            return True
        else:
            self.log("Assistant timeout", "WARN")
            return True

    def start_web(self):
        """Start the web server."""
        from web import create_app
        app = create_app()
        
        self.log(f"Interface web sur http://localhost:{WEB_PORT}", "OK")
        
        # Open browser after a short delay
        def open_browser():
            time.sleep(2)
            webbrowser.open(f"http://localhost:{WEB_PORT}")
        
        threading.Thread(target=open_browser, daemon=True).start()
        
        # Run Flask in main thread
        app.run(host='0.0.0.0', port=WEB_PORT, debug=False, use_reloader=False)

    def cleanup(self):
        """Stop all processes."""
        self.log("Arrêt des services...")
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()
        self.log("Services arrêtés", "OK")

    def run(self):
        """Main entry point."""
        print("\n" + "="*50)
        print("🏥 Open Medical Secretary")
        print("="*50 + "\n")
        
        # Handle CTRL+C
        def signal_handler(sig, frame):
            self.running = False
            self.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start services
        self.start_ollama()
        self.start_tts()
        self.start_assistant()
        
        # Start web interface (blocking)
        try:
            self.start_web()
        except Exception as e:
            self.log(f"Erreur web: {e}", "ERROR")
            self.cleanup()


def main():
    # Check if first run
    base_dir = Path(__file__).parent
    env_file = base_dir / ".env"
    
    if not env_file.exists():
        print("\n🔧 Première exécution détectée!")
        print("L'assistant de configuration va s'ouvrir dans votre navigateur.\n")
    
    app = OpenMedicalSecretary()
    app.run()


if __name__ == "__main__":
    main()
