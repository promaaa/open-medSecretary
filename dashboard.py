#!/usr/bin/env python3
"""
🚀 Live Dashboard - Lance et monitore tout le pipeline

Une seule commande pour tout lancer avec suivi en temps réel!
Inclut la configuration téléphonie au premier lancement.

Usage:
    python dashboard.py           # Lance le dashboard
    python dashboard.py --test    # Lance avec test automatique
    python dashboard.py --setup   # Force la configuration téléphonie
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
from pathlib import Path

# Rich for beautiful terminal UI
try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Installation de l'interface graphique...")
    subprocess.run([sys.executable, "-m", "pip", "install", "rich", "-q"])
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.prompt import Prompt, Confirm

console = Console()

# =============================================================================
# TELEPHONY CONFIGURATION
# =============================================================================

def get_env_path() -> Path:
    return Path(__file__).parent / ".env"


def load_env() -> dict:
    """Load environment variables from .env file."""
    env = {}
    env_path = get_env_path()
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env[key] = value
    return env


def save_env(config: dict):
    """Save configuration to .env file."""
    env_path = get_env_path()
    existing = load_env()
    existing.update(config)
    
    with open(env_path, "w") as f:
        f.write("# Open Medical Secretary - Configuration\n")
        f.write(f"# Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        for key, value in existing.items():
            f.write(f"{key}={value}\n")


def is_telephony_configured() -> bool:
    """Check if telephony is already configured."""
    env = load_env()
    return bool(env.get("SIP_USERNAME") and env.get("SIP_PASSWORD"))


def check_docker_running() -> bool:
    """Check if Docker is available."""
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False


def is_asterisk_running() -> bool:
    """Check if Asterisk container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=open-med-asterisk", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=5
        )
        return "open-med-asterisk" in result.stdout
    except:
        return False


def setup_telephony_interactive():
    """Interactive telephony setup."""
    console.print("\n[bold cyan]📞 Configuration Téléphonie[/bold cyan]\n")
    
    console.print("Pour recevoir des appels, vous devez connecter un numéro de téléphone.")
    console.print("Choisissez votre opérateur SIP:\n")
    
    console.print("  [1] OVH Télécom [dim](recommandé France)[/dim]")
    console.print("  [2] Twilio [dim](international)[/dim]")
    console.print("  [3] Free SIP [dim](Freebox)[/dim]")
    console.print("  [4] Autre opérateur")
    console.print("  [5] Passer [dim](configurer plus tard)[/dim]")
    console.print()
    
    choice = Prompt.ask("Votre choix", choices=["1", "2", "3", "4", "5"], default="5")
    
    if choice == "5":
        console.print("[yellow]Configuration téléphonie ignorée.[/yellow]")
        console.print("Vous pouvez la faire plus tard avec: python setup_telephony.py\n")
        return False
    
    providers = {
        "1": ("OVH", "siptrunk.ovh.net", "https://www.ovhtelecom.fr/manager/"),
        "2": ("Twilio", "", "https://console.twilio.com/"),
        "3": ("Free", "freephonie.net", "https://subscribe.free.fr/login/"),
        "4": ("Autre", "", ""),
    }
    
    provider_name, default_server, help_url = providers[choice]
    
    console.print(f"\n[bold]Configuration {provider_name}[/bold]")
    if help_url:
        console.print(f"[dim]Aide: {help_url}[/dim]\n")
    
    if choice == "2":  # Twilio needs custom server
        server = Prompt.ask("Serveur SIP (ex: xxxxx.pstn.twilio.com)")
    elif choice == "4":  # Custom
        server = Prompt.ask("Serveur SIP")
    else:
        server = default_server
    
    port = Prompt.ask("Port SIP", default="5060")
    username = Prompt.ask("Identifiant SIP")
    password = Prompt.ask("Mot de passe SIP", password=True)
    
    config = {
        "SIP_SERVER": server,
        "SIP_PORT": port,
        "SIP_USERNAME": username,
        "SIP_PASSWORD": password,
    }
    
    save_env(config)
    console.print("\n[green]✅ Configuration sauvegardée![/green]\n")
    
    return True


def start_asterisk_docker():
    """Start Asterisk Docker container."""
    console.print("[dim]Démarrage d'Asterisk...[/dim]")
    
    result = subprocess.run(
        ["docker-compose", "up", "-d", "asterisk"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    if result.returncode == 0:
        console.print("[green]✅ Asterisk démarré[/green]")
        return True
    else:
        console.print(f"[red]❌ Erreur Asterisk: {result.stderr}[/red]")
        return False


# =============================================================================
# DASHBOARD STATE
# =============================================================================

class DashboardState:
    def __init__(self):
        self.services = {
            "asterisk": {"status": "⏳", "name": "📞 Asterisk PBX", "port": 5060},
            "ollama": {"status": "⏳", "name": "🧠 Ollama LLM", "port": 11434},
            "tts": {"status": "⏳", "name": "🔊 Coqui TTS", "port": 5555},
            "main": {"status": "⏳", "name": "🤖 Assistant IA", "port": 9001},
        }
        self.logs = deque(maxlen=15)
        self.stats = {
            "calls": 0,
            "transcriptions": 0,
            "responses": 0,
            "errors": 0,
        }
        self.processes = []
        self.running = True
        self.telephony_configured = False
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = {"INFO": "white", "OK": "green", "ERROR": "red", "WARN": "yellow"}.get(level, "white")
        self.logs.append(f"[{color}]{timestamp} [{level}] {message}[/{color}]")

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
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# =============================================================================
# SERVICE MANAGEMENT
# =============================================================================

def check_port(port: int) -> bool:
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
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except:
        return False


async def start_asterisk():
    """Start Asterisk if configured."""
    if not state.telephony_configured:
        state.services["asterisk"]["status"] = "⚪"
        state.log("Téléphonie non configurée", "WARN")
        return False
    
    if not check_docker_running():
        state.services["asterisk"]["status"] = "❌"
        state.log("Docker non disponible", "ERROR")
        return False
    
    state.log("Démarrage Asterisk...")
    
    if is_asterisk_running():
        state.services["asterisk"]["status"] = "✅"
        state.log("Asterisk déjà actif", "OK")
        return True
    
    # Start Asterisk
    result = subprocess.run(
        ["docker-compose", "up", "-d", "asterisk"],
        capture_output=True,
        cwd=Path(__file__).parent
    )
    
    if result.returncode == 0:
        await asyncio.sleep(3)
        if is_asterisk_running():
            state.services["asterisk"]["status"] = "✅"
            state.log("Asterisk démarré", "OK")
            return True
    
    state.services["asterisk"]["status"] = "❌"
    state.log("Échec Asterisk", "ERROR")
    return False


async def start_ollama():
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
    state.log("Échec Ollama", "ERROR")
    return False


async def start_tts():
    state.log("Vérification TTS...")
    
    if check_port(5555):
        state.services["tts"]["status"] = "✅"
        state.log("TTS déjà actif", "OK")
        return True
    
    state.log("Démarrage TTS (~10s)...")
    
    p = subprocess.Popen(
        [sys.executable, "coqui_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=Path(__file__).parent
    )
    state.processes.append(p)
    
    def monitor():
        for line in p.stdout:
            line = line.decode().strip()
            if "Synthesizing" in line:
                state.stats["responses"] += 1
    
    threading.Thread(target=monitor, daemon=True).start()
    
    for _ in range(30):
        await asyncio.sleep(1)
        if check_port(5555):
            state.services["tts"]["status"] = "✅"
            state.log("TTS démarré", "OK")
            return True
    
    state.services["tts"]["status"] = "❌"
    state.log("Échec TTS", "ERROR")
    return False


async def start_main():
    state.log("Démarrage assistant...")
    
    if check_port(9001):
        state.services["main"]["status"] = "✅"
        state.log("Assistant déjà actif", "OK")
        return True
    
    p = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=Path(__file__).parent
    )
    state.processes.append(p)
    
    def monitor():
        for line in p.stdout:
            line = line.decode().strip()
            if "connection from" in line.lower():
                state.stats["calls"] += 1
                state.log("📞 Appel entrant!", "OK")
            elif "error" in line.lower():
                state.stats["errors"] += 1
    
    threading.Thread(target=monitor, daemon=True).start()
    
    for _ in range(15):
        await asyncio.sleep(1)
        if check_port(9001):
            state.services["main"]["status"] = "✅"
            state.log("Assistant démarré", "OK")
            return True
    
    state.services["main"]["status"] = "❌"
    state.log("Échec assistant", "ERROR")
    return False


# =============================================================================
# UI COMPONENTS
# =============================================================================

def create_services_table() -> Table:
    table = Table(title="🔧 Services", box=None, padding=(0, 1))
    table.add_column("Service", style="cyan")
    table.add_column("Status")
    table.add_column("Port", style="dim")
    
    for key, svc in state.services.items():
        table.add_row(svc["name"], svc["status"], str(svc["port"]))
    
    return table


def create_stats_table() -> Table:
    table = Table(title="📊 Stats", box=None, padding=(0, 1))
    table.add_column("", style="cyan")
    table.add_column("", style="green")
    
    table.add_row("Appels", str(state.stats["calls"]))
    table.add_row("Réponses", str(state.stats["responses"]))
    table.add_row("Erreurs", str(state.stats["errors"]))
    
    return table


def create_logs_panel() -> Panel:
    logs_text = Text()
    for log in state.logs:
        logs_text.append(log + "\n", style=None)
    return Panel(logs_text, title="📋 Logs", border_style="blue")


def create_layout() -> Layout:
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
    header = Text()
    header.append("🏥 ", style="bold")
    header.append("Open Medical Secretary", style="bold cyan")
    if state.telephony_configured:
        header.append(" | 📞 Téléphonie active", style="green")
    layout["header"].update(Panel(header, style="bold"))
    
    # Footer
    core_ok = all(state.services[s]["status"] == "✅" for s in ["ollama", "tts", "main"])
    if core_ok:
        footer = "✅ Prêt! | Ctrl+C pour quitter"
        if not state.telephony_configured:
            footer += " | python setup_telephony.py pour configurer le téléphone"
    else:
        footer = "⏳ Démarrage..."
    layout["footer"].update(Panel(footer, style="dim"))
    
    return layout


# =============================================================================
# MAIN
# =============================================================================

async def main(run_test: bool = False, force_setup: bool = False):
    console.clear()
    console.print("[bold cyan]🏥 Open Medical Secretary[/bold cyan]\n")
    
    # Check telephony configuration
    state.telephony_configured = is_telephony_configured()
    
    if force_setup or not state.telephony_configured:
        if not state.telephony_configured:
            console.print("[yellow]⚠️ Téléphonie non configurée[/yellow]\n")
        
        if Confirm.ask("Configurer la téléphonie maintenant?", default=False):
            setup_telephony_interactive()
            state.telephony_configured = is_telephony_configured()
    
    console.print("Démarrage des services...\n")
    
    # Start all services
    await start_asterisk()
    await start_ollama()
    await start_tts()
    await start_main()
    
    state.log("🎉 Initialisation terminée!", "OK")
    
    # Run live dashboard
    with Live(create_layout(), refresh_per_second=2, console=console) as live:
        while state.running:
            live.update(create_layout())
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dashboard Open Medical Secretary")
    parser.add_argument("--test", action="store_true", help="Lance un test automatique")
    parser.add_argument("--setup", action="store_true", help="Force la configuration téléphonie")
    args = parser.parse_args()
    
    try:
        asyncio.run(main(run_test=args.test, force_setup=args.setup))
    except KeyboardInterrupt:
        console.print("\n[yellow]Arrêt...[/yellow]")
