#!/usr/bin/env python3
"""
🚀 Live Dashboard - Lance et monitore tout le pipeline

Une seule commande pour tout lancer avec suivi en temps réel!

Usage:
    python dashboard.py           # Lance le dashboard
    python dashboard.py --test    # Lance avec test automatique
"""

import argparse
import asyncio
import atexit
import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime

# Rich for beautiful terminal UI
try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Installing rich for better UI...")
    subprocess.run([sys.executable, "-m", "pip", "install", "rich", "-q"])
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

console = Console()

# Global state
class DashboardState:
    def __init__(self):
        self.services = {
            "ollama": {"status": "⏳", "name": "Ollama LLM", "port": 11434},
            "tts": {"status": "⏳", "name": "Coqui TTS", "port": 5555},
            "main": {"status": "⏳", "name": "Voice Assistant", "port": 9001},
        }
        self.logs = deque(maxlen=20)
        self.stats = {
            "calls": 0,
            "transcriptions": 0,
            "responses": 0,
            "errors": 0,
        }
        self.processes = []
        self.running = True
        self.last_activity = None
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = {"INFO": "white", "OK": "green", "ERROR": "red", "WARN": "yellow"}.get(level, "white")
        self.logs.append(f"[{color}]{timestamp} [{level}] {message}[/{color}]")
        self.last_activity = message

state = DashboardState()


def cleanup():
    """Cleanup all processes on exit."""
    state.running = False
    for p in state.processes:
        try:
            p.terminate()
            p.wait(timeout=2)
        except:
            try:
                p.kill()
            except:
                pass

atexit.register(cleanup)

def signal_handler(sig, frame):
    state.running = False
    cleanup()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


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


def check_ollama() -> bool:
    """Check if Ollama is running."""
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except:
        return False


async def start_ollama():
    """Start Ollama service."""
    state.log("Vérification Ollama...")
    
    if check_ollama():
        state.services["ollama"]["status"] = "✅"
        state.log("Ollama déjà actif", "OK")
        return True
    
    state.log("Démarrage Ollama...")
    p = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    state.processes.append(p)
    
    for _ in range(10):
        await asyncio.sleep(1)
        if check_ollama():
            state.services["ollama"]["status"] = "✅"
            state.log("Ollama démarré", "OK")
            return True
    
    state.services["ollama"]["status"] = "❌"
    state.log("Échec démarrage Ollama", "ERROR")
    return False


async def start_tts():
    """Start Coqui TTS server."""
    state.log("Vérification TTS...")
    
    if check_port(5555):
        state.services["tts"]["status"] = "✅"
        state.log("TTS déjà actif", "OK")
        return True
    
    state.log("Démarrage TTS (chargement modèle ~10s)...")
    
    p = subprocess.Popen(
        [sys.executable, "coqui_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    state.processes.append(p)
    
    # Monitor TTS output
    def monitor_tts():
        for line in p.stdout:
            line = line.decode().strip()
            if "Model loaded" in line or "server running" in line:
                state.log("TTS prêt", "OK")
            elif "Synthesizing" in line:
                state.stats["responses"] += 1
                state.log("TTS: Synthèse en cours...", "INFO")
    
    threading.Thread(target=monitor_tts, daemon=True).start()
    
    for _ in range(30):
        await asyncio.sleep(1)
        if check_port(5555):
            state.services["tts"]["status"] = "✅"
            state.log("TTS démarré", "OK")
            return True
    
    state.services["tts"]["status"] = "❌"
    state.log("Échec démarrage TTS", "ERROR")
    return False


async def start_main():
    """Start main voice assistant."""
    state.log("Démarrage assistant vocal...")
    
    if check_port(9001):
        state.services["main"]["status"] = "✅"
        state.log("Assistant déjà actif", "OK")
        return True
    
    p = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    state.processes.append(p)
    
    # Monitor main output
    def monitor_main():
        for line in p.stdout:
            line = line.decode().strip()
            if "connection from" in line.lower():
                state.stats["calls"] += 1
                state.log("📞 Nouvel appel!", "OK")
            elif "transcri" in line.lower():
                state.stats["transcriptions"] += 1
            elif "error" in line.lower():
                state.stats["errors"] += 1
                state.log(f"Erreur: {line[:50]}", "ERROR")
            elif "Ready to receive" in line:
                state.log("Assistant prêt!", "OK")
    
    threading.Thread(target=monitor_main, daemon=True).start()
    
    for _ in range(15):
        await asyncio.sleep(1)
        if check_port(9001):
            state.services["main"]["status"] = "✅"
            state.log("Assistant démarré", "OK")
            return True
    
    state.services["main"]["status"] = "❌"
    state.log("Échec démarrage assistant", "ERROR")
    return False


def create_services_table() -> Table:
    """Create services status table."""
    table = Table(title="🔧 Services", box=None, padding=(0, 1))
    table.add_column("Service", style="cyan")
    table.add_column("Status")
    table.add_column("Port", style="dim")
    
    for key, svc in state.services.items():
        table.add_row(svc["name"], svc["status"], str(svc["port"]))
    
    return table


def create_stats_table() -> Table:
    """Create statistics table."""
    table = Table(title="📊 Statistiques", box=None, padding=(0, 1))
    table.add_column("Métrique", style="cyan")
    table.add_column("Valeur", style="green")
    
    table.add_row("Appels", str(state.stats["calls"]))
    table.add_row("Transcriptions", str(state.stats["transcriptions"]))
    table.add_row("Réponses TTS", str(state.stats["responses"]))
    table.add_row("Erreurs", str(state.stats["errors"]))
    
    return table


def create_logs_panel() -> Panel:
    """Create logs panel."""
    logs_text = Text()
    for log in state.logs:
        logs_text.append(log + "\n", style=None)
    
    return Panel(logs_text, title="📋 Logs", border_style="blue")


def create_layout() -> Layout:
    """Create the dashboard layout."""
    layout = Layout()
    
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3),
    )
    
    layout["body"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=2),
    )
    
    layout["left"].split_column(
        Layout(create_services_table(), name="services"),
        Layout(create_stats_table(), name="stats"),
    )
    
    layout["right"].update(create_logs_panel())
    
    # Header
    header_text = Text()
    header_text.append("🏥 ", style="bold")
    header_text.append("Open Medical Secretary", style="bold cyan")
    header_text.append(" - Dashboard Live", style="dim")
    layout["header"].update(Panel(header_text, style="bold"))
    
    # Footer
    all_ok = all(s["status"] == "✅" for s in state.services.values())
    if all_ok:
        footer_text = "✅ Prêt! Test: python tests/mock_audiosocket_client.py | Ctrl+C pour quitter"
    else:
        footer_text = "⏳ Démarrage en cours..."
    layout["footer"].update(Panel(footer_text, style="dim"))
    
    return layout


async def run_test():
    """Run automated test."""
    state.log("Lancement test automatique...")
    await asyncio.sleep(2)
    
    # Create test audio
    state.log("Création audio de test...")
    result = subprocess.run(
        [sys.executable, "-c", """
import sys
sys.path.insert(0, '.')
from TTS.api import TTS
import numpy as np
import wave
from scipy import signal

tts = TTS('tts_models/fr/css10/vits')
wav = tts.tts("Bonjour, je voudrais prendre un rendez-vous.")
audio = (np.array(wav) * 32767).astype(np.int16)
resampled = signal.resample(audio, int(len(audio) * 8000 / 22050)).astype(np.int16)

with wave.open('/tmp/dashboard_test.wav', 'wb') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(8000)
    f.writeframes(resampled.tobytes())
print("OK")
"""],
        capture_output=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    if result.returncode == 0:
        state.log("Audio de test créé", "OK")
    else:
        state.log("Échec création audio", "ERROR")
        return
    
    # Run test client
    state.log("Appel test en cours...")
    result = subprocess.run(
        [sys.executable, "tests/mock_audiosocket_client.py", "--audio-file", "/tmp/dashboard_test.wav"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    if "Saved" in result.stdout and "bytes" in result.stdout:
        state.log("✅ Test réussi! Réponse reçue", "OK")
        state.log("Écouter: afplay response.wav", "INFO")
    else:
        state.log("Test échoué", "ERROR")


async def main(run_test_flag: bool = False):
    """Main dashboard loop."""
    
    console.clear()
    console.print("[bold cyan]🏥 Open Medical Secretary - Dashboard[/bold cyan]\n")
    console.print("Démarrage des services...\n")
    
    # Start services
    await start_ollama()
    await start_tts()
    await start_main()
    
    # Check all services
    all_ok = all(s["status"] == "✅" for s in state.services.values())
    
    if not all_ok:
        console.print("\n[red]❌ Certains services n'ont pas démarré.[/red]")
        console.print("Vérifiez les logs ci-dessus.")
        return
    
    state.log("🎉 Tous les services sont prêts!", "OK")
    
    # Start test if requested
    if run_test_flag:
        asyncio.create_task(run_test())
    
    # Run live dashboard
    with Live(create_layout(), refresh_per_second=2, console=console) as live:
        while state.running:
            live.update(create_layout())
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dashboard Live")
    parser.add_argument("--test", action="store_true", help="Lance un test automatique")
    args = parser.parse_args()
    
    try:
        asyncio.run(main(run_test_flag=args.test))
    except KeyboardInterrupt:
        console.print("\n[yellow]Arrêt du dashboard...[/yellow]")
