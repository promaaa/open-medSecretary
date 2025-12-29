# Secrétariat Médical Vocal Souverain

Agent vocal IA 100% On-Premise pour cabinets médicaux, utilisant [Pipecat](https://github.com/pipecat-ai/pipecat).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Cabinet Médical                          │
│  ┌─────────────┐                                                │
│  │  Téléphone  │◄────────► Asterisk PBX                         │
│  └─────────────┘              │                                 │
│                               │ AudioSocket (TCP:9001)          │
│                               ▼                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Voice Assistant                          ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        ││
│  │  │ Whisper │  │ Ollama  │  │  Piper  │  │ Silero  │        ││
│  │  │  (STT)  │  │  (LLM)  │  │  (TTS)  │  │  (VAD)  │        ││
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        ││
│  │                    Pipecat Pipeline                         ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
              100% Local - Aucune donnée vers le cloud
```

## Prérequis

- Python 3.10+
- GPU NVIDIA (recommandé) ou Apple Silicon
- Ollama installé et configuré
- Serveur Piper TTS

## Installation

```bash
# 1. Cloner et installer les dépendances
cd medical_voice_assistant
pip install -r requirements.txt

# 2. Démarrer Ollama avec un modèle
ollama run llama3:8b

# 3. Démarrer Piper TTS (Docker)
docker run -p 5000:5000 rhasspy/piper-tts-server:latest --voice fr_FR-siwis-medium

# 4. Configurer l'environnement
cp .env.example .env
# Éditer .env selon vos besoins

# 5. Lancer l'assistant
python main.py
```

## Configuration Asterisk

Dans `extensions.conf`:

```ini
[from-internal]
exten => 1000,1,Answer()
same => n,AudioSocket(127.0.0.1:9001,${CHANNEL(uniqueid)})
same => n,Hangup()
```

## Test sans Asterisk

```bash
python tests/mock_audiosocket_client.py
```

## Structure du Projet

```
medical_voice_assistant/
├── main.py                     # Point d'entrée principal
├── requirements.txt            # Dépendances Python
├── .env.example               # Configuration exemple
├── transports/
│   └── audiosocket/
│       └── transport.py       # Transport AudioSocket custom
├── services/
│   └── medical_llm.py         # Service LLM médical
├── config/
│   └── system_prompts.py      # Prompts système
└── tests/
    └── mock_audiosocket_client.py  # Client de test
```

## Licence

BSD 2-Clause License
