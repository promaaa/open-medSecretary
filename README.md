# Open Medical Secretary

🩺 **100% On-Premise AI Voice Assistant for Medical Offices**

Built with [Pipecat](https://github.com/pipecat-ai/pipecat) - zero cloud dependencies, all patient data stays local.

## Features

- 🎙️ **Speech Recognition**: Whisper (faster-whisper, French)
- 🧠 **AI Response**: Ollama (llama3:8b, local)
- 🔊 **Voice Synthesis**: Coqui TTS (VITS French model, natural voice)
- 📞 **Telephony**: Asterisk AudioSocket integration
- 🔒 **Privacy**: No data sent to cloud

## Architecture

```
Asterisk PBX ←→ AudioSocket (TCP:9001) ←→ Pipecat Pipeline
                                              ↓
                          [STT] → [LLM] → [TTS]
                        Whisper  Ollama   Coqui
```

## Quick Start

### 1. Install Dependencies

```bash
cd medical_voice_assistant
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install TTS  # Coqui TTS
```

### 2. Start Ollama

```bash
ollama run llama3:8b
```

### 3. Start TTS Server

```bash
python coqui_server.py
```

### 4. Start Voice Assistant

```bash
python main.py
```

### 5. Test

```bash
python tests/mock_audiosocket_client.py
afplay response.wav  # Listen to greeting
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# STT
WHISPER_MODEL=small
WHISPER_LANGUAGE=FR

# LLM
OLLAMA_MODEL=llama3:8b

# TTS  
TTS_MODEL=tts_models/fr/css10/vits
```

## Asterisk Integration

Add to `extensions.conf`:

```ini
[medical-secretary]
exten => 1000,1,Answer()
same => n,AudioSocket(127.0.0.1:9001,${CHANNEL(uniqueid)})
same => n,Hangup()
```

## Project Structure

```
├── main.py              # Pipeline orchestration
├── coqui_server.py      # Coqui TTS HTTP server
├── transports/          # AudioSocket transport
├── services/            # Medical LLM service
├── config/              # System prompts (French)
└── tests/               # Mock AudioSocket client
```

## License

BSD 2-Clause License
