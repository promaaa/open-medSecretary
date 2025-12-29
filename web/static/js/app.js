// Open Medical Secretary - Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function () {
    // Initialize
    updateStatus();
    setInterval(updateStatus, 3000);

    // Event listeners
    document.getElementById('test-btn')?.addEventListener('click', runTest);
    document.getElementById('start-btn')?.addEventListener('click', toggleAssistant);
});

// Update service status
async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // Update services
        updateService('ollama', data.services.ollama);
        updateService('tts', data.services.tts);
        updateService('assistant', data.services.assistant);
        updateService('asterisk', data.services.asterisk);

        // Update connection badge
        const badge = document.getElementById('connection-status');
        const dot = badge.querySelector('.status-dot');
        const text = badge.querySelector('span:last-child');

        if (data.running) {
            dot.classList.add('connected');
            text.textContent = 'Connecté';
        } else {
            dot.classList.remove('connected');
            text.textContent = 'En attente...';
        }

        // Update start button
        const startBtn = document.getElementById('start-btn');
        if (startBtn) {
            if (data.running) {
                startBtn.innerHTML = '<i data-lucide="square"></i> Arrêter';
                startBtn.classList.add('btn-danger');
                startBtn.classList.remove('btn-primary');
            } else {
                startBtn.innerHTML = '<i data-lucide="play"></i> Démarrer';
                startBtn.classList.remove('btn-danger');
                startBtn.classList.add('btn-primary');
            }
            lucide.createIcons();
        }

    } catch (error) {
        console.error('Status update failed:', error);
    }
}

function updateService(name, isRunning) {
    const card = document.getElementById(`service-${name}`);
    const status = document.getElementById(`status-${name}`);

    if (card && status) {
        card.classList.remove('running', 'stopped', 'error');
        card.classList.add(isRunning ? 'running' : 'stopped');
        status.textContent = isRunning ? '✅' : '⭕';
    }
}

// Run test
async function runTest() {
    try {
        const response = await fetch('/api/test');
        const data = await response.json();
        alert(data.message);
    } catch (error) {
        alert('Erreur lors du test');
    }
}

// Toggle assistant
async function toggleAssistant() {
    alert('Pour démarrer/arrêter l\'assistant, utilisez le terminal.');
}

// Save configuration
async function saveConfig(event) {
    event.preventDefault();

    const form = event.target;
    const data = {
        sip_server: form.sip_server.value,
        sip_username: form.sip_username.value,
        sip_password: form.sip_password.value,
        doctor_phone: form.doctor_phone.value,
        ollama_model: form.ollama_model?.value || 'llama3.2:3b'
    };

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            alert('Configuration sauvegardée !');
        } else {
            alert('Erreur lors de la sauvegarde');
        }
    } catch (error) {
        alert('Erreur de connexion');
    }
}
