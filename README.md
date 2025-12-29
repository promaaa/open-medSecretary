# 🏥 Open Medical Secretary

**AI voice assistant for medical practices**

Automatic call assistant that handles inbound calls, scheduling, and emergencies — 100% local with no cloud dependency.

---

## ⚡ Quick install

```bash
# Clone the project
git clone https://github.com/promaaa/open-medSecretary.git
cd open-medical-secretary

# Install (single command)
./install.sh

# Start
./start.py
```

The web dashboard opens automatically at `http://localhost:3000`.

---

## 🎯 Features

- **📞 IVR voice menu**: Options for appointments, emergencies, and other requests
- **🤖 AI assistant**: Answers callers and schedules appointments
- **🔊 Text-to-speech**: Natural French voice (Coqui TTS)
- **🧠 100% local**: No data sent to the cloud (Ollama + Whisper)
- **📊 Dashboard**: Web UI for monitoring and configuration

---

## 📋 Voice menu

When a patient calls:

| Key | Action |
|-----|--------|
| **1** | Appointment handling → AI assistant |
| **2** | Emergency → Transfer to doctor |
| **3** | Other request → AI assistant |
| **\*** | Repeat the menu |

---

## 🔧 Configuration

### First run

1. Run `./start.py`
2. Open **Configuration** in the dashboard
3. Enter your SIP credentials (OVH, Twilio, Free, etc.)
4. Enter the doctor’s number for emergencies

### Supported SIP providers

- **OVH Télécom** (recommended in France)
- **Twilio** (international)
- **Free SIP** (Freebox)
- Any standard SIP provider

---

## 📁 Project structure

```
open-medical-secretary/
├── start.py          # Main launcher
├── install.sh        # Installer
├── web.py            # Flask web interface
├── backend/          # AI core (Pipecat, STT, TTS)
├── telephony/        # Asterisk configuration
├── web/              # Templates & assets
└── data/             # Call logs
```

---

## 🛠️ Requirements

- **macOS** or **Linux**
- **Python 3.10+**
- **Ollama** (installed automatically)
- **Docker** (optional, for Asterisk)

---

## 📞 Telephony (optional)

To connect your phone number:

```bash
cd telephony
docker-compose up -d
```

---

## 📄 License

MIT License - Open source project
