# Open Medical Secretary

100% On-Premise AI voice assistant for medical offices, built with [Pipecat](https://github.com/pipecat-ai/pipecat).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Medical Office                           │
│  ┌─────────────┐                                                │
│  │  Telephone  │◄────────► Asterisk PBX                         │
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
              100% Local - No data sent to cloud
```

## Prerequisites

- Python 3.10+
- NVIDIA GPU (recommended) or Apple Silicon
- Ollama installed and configured
- Piper TTS server

## Installation

```bash
# 1. Clone and install dependencies
cd medical_voice_assistant
pip install -r requirements.txt

# 2. Start Ollama with a model
ollama run llama3:8b

# 3. Start Piper TTS (Docker)
docker run -p 5000:5000 rhasspy/piper-tts-server:latest --voice en_US-lessac-medium

# 4. Configure environment
cp .env.example .env
# Edit .env as needed

# 5. Run the assistant
python main.py
```

## Asterisk Configuration

In `extensions.conf`:

```ini
[from-internal]
exten => 1000,1,Answer()
same => n,AudioSocket(127.0.0.1:9001,${CHANNEL(uniqueid)})
same => n,Hangup()
```

## Testing Without Asterisk

```bash
python tests/mock_audiosocket_client.py
```

## Project Structure

```
medical_voice_assistant/
├── main.py                     # Main entry point
├── requirements.txt            # Python dependencies
├── .env.example               # Example configuration
├── transports/
│   └── audiosocket/
│       └── transport.py       # Custom AudioSocket transport
├── services/
│   └── medical_llm.py         # Medical LLM service
├── config/
│   └── system_prompts.py      # System prompts
└── tests/
    └── mock_audiosocket_client.py  # Test client
```

## License

BSD 2-Clause License
