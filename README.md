# 🏥 Open Medical Secretary

**Assistant vocal IA pour cabinets médicaux**

Secrétaire téléphonique automatique qui gère les appels, prises de rendez-vous et urgences - 100% local, sans cloud.

---

## ⚡ Installation rapide

```bash
# Cloner le projet
git clone https://github.com/promaaa/open-medSecretary.git
cd open-medical-secretary

# Installer (une seule commande)
./install.sh

# Lancer
./start.py
```

L'interface web s'ouvre automatiquement sur `http://localhost:3000`

---

## 🎯 Fonctionnalités

- **📞 Menu vocal IVR** : Options pour RDV, urgences, autres demandes
- **🤖 Assistant IA** : Répond aux patients, prend les RDV
- **🔊 Synthèse vocale** : Voix naturelle en français (Coqui TTS)
- **🧠 100% Local** : Pas de données envoyées au cloud (Ollama + Whisper)
- **📊 Dashboard** : Interface web pour surveiller et configurer

---

## 📋 Menu vocal

Quand un patient appelle :

| Touche | Action |
|--------|--------|
| **1** | Gestion des RDV → Assistant IA |
| **2** | Urgence → Transfert au médecin |
| **3** | Autre demande → Assistant IA |
| **\*** | Répéter le menu |

---

## 🔧 Configuration

### Première utilisation

1. Lancez `./start.py`
2. Allez dans **Configuration** depuis le dashboard
3. Entrez vos identifiants SIP (OVH, Twilio, Free...)
4. Entrez le numéro du médecin pour les urgences

### Opérateurs SIP supportés

- **OVH Télécom** (recommandé France)
- **Twilio** (international)
- **Free SIP** (Freebox)
- Tout opérateur SIP standard

---

## 📁 Structure

```
open-medical-secretary/
├── start.py          # Lanceur principal
├── install.sh        # Installateur
├── web.py            # Interface web Flask
├── backend/          # Core IA (Pipecat, STT, TTS)
├── telephony/        # Config Asterisk
├── web/              # Templates & assets
└── data/             # Logs d'appels
```

---

## 🛠️ Prérequis

- **macOS** ou **Linux**
- **Python 3.10+**
- **Ollama** (installé automatiquement)
- **Docker** (optionnel, pour Asterisk)

---

## 📞 Téléphonie (optionnel)

Pour connecter votre numéro de téléphone :

```bash
cd telephony
docker-compose up -d
```

---

## 📄 Licence

MIT License - Projet open source
