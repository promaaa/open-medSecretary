#!/bin/bash
# ==================================================
# Open Medical Secretary - Installation Script
# One-click installer for Mac/Linux
# ==================================================

set -e

echo ""
echo "=================================================="
echo "🏥 Open Medical Secretary - Installation"
echo "=================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check OS
OS="$(uname -s)"
if [[ "$OS" != "Darwin" && "$OS" != "Linux" ]]; then
    log_error "Ce script supporte uniquement Mac et Linux"
    exit 1
fi

# Check if running from correct directory
if [[ ! -f "start.py" ]]; then
    log_error "Exécutez ce script depuis le répertoire open-medical-secretary"
    exit 1
fi

# ==================================================
# 1. Check Python
# ==================================================
log_info "Vérification de Python..."

if command -v python3 &> /dev/null; then
    PYTHON=python3
    log_info "Python trouvé: $(python3 --version)"
else
    log_error "Python 3 non trouvé. Installez-le d'abord."
    if [[ "$OS" == "Darwin" ]]; then
        echo "  brew install python3"
    else
        echo "  sudo apt install python3 python3-pip"
    fi
    exit 1
fi

# ==================================================
# 2. Create virtual environment
# ==================================================
log_info "Création de l'environnement virtuel..."

if [[ ! -d "venv" ]]; then
    $PYTHON -m venv venv
fi

source venv/bin/activate
log_info "Environnement virtuel activé"

# ==================================================
# 3. Install Python dependencies
# ==================================================
log_info "Installation des dépendances Python..."

pip install --upgrade pip -q
pip install -r requirements.txt -q

log_info "Dépendances Python installées ✓"

# ==================================================
# 4. Check/Install Ollama
# ==================================================
log_info "Vérification d'Ollama..."

if ! command -v ollama &> /dev/null; then
    log_warn "Ollama non trouvé. Installation..."
    
    if [[ "$OS" == "Darwin" ]]; then
        # Mac - use homebrew or curl
        if command -v brew &> /dev/null; then
            brew install ollama
        else
            curl -fsSL https://ollama.com/install.sh | sh
        fi
    else
        # Linux
        curl -fsSL https://ollama.com/install.sh | sh
    fi
fi

log_info "Ollama installé ✓"

# ==================================================
# 5. Download AI Model
# ==================================================
log_info "Téléchargement du modèle IA (peut prendre quelques minutes)..."

ollama pull llama3.2:3b 2>/dev/null || log_warn "Modèle déjà présent ou erreur (non bloquant)"

log_info "Modèle IA prêt ✓"

# ==================================================
# 6. Create data directories
# ==================================================
log_info "Création des répertoires..."

mkdir -p data models

# ==================================================
# 7. Done!
# ==================================================
echo ""
echo "=================================================="
echo "✅ Installation terminée!"
echo "=================================================="
echo ""
echo "Pour démarrer l'assistant:"
echo ""
echo "  ./start.py"
echo ""
echo "Ou avec le virtual environment:"
echo ""
echo "  source venv/bin/activate"
echo "  python start.py"
echo ""
echo "L'interface web s'ouvrira automatiquement sur:"
echo "  http://localhost:3000"
echo ""
