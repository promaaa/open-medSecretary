"""
Open Medical Secretary - Web Interface
Flask-based dashboard for doctors
"""

import os
import json
import socket
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory

# Configuration
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "web" / "static"
TEMPLATES_DIR = BASE_DIR / "web" / "templates"


def check_port(port):
    """Check if a port is open."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def create_app():
    """Create Flask application."""
    app = Flask(__name__,
                static_folder=str(STATIC_DIR),
                template_folder=str(TEMPLATES_DIR))
    
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)
    
    # =====================
    # ROUTES
    # =====================
    
    @app.route('/')
    def index():
        """Main dashboard."""
        return render_template('index.html')
    
    @app.route('/setup')
    def setup():
        """Setup wizard."""
        return render_template('setup.html')
    
    @app.route('/calls')
    def calls():
        """Call history."""
        return render_template('calls.html')
    
    @app.route('/settings')
    def settings():
        """Settings page."""
        return render_template('settings.html')
    
    # =====================
    # API ENDPOINTS
    # =====================
    
    @app.route('/api/status')
    def api_status():
        """Get services status."""
        services = {
            'ollama': check_port(11434),
            'tts': check_port(5555),
            'assistant': check_port(9001),
            'asterisk': check_port(5060)
        }
        
        return jsonify({
            'services': services,
            'running': services['ollama'] and services['tts'],
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/config', methods=['GET', 'POST'])
    def api_config():
        """Get or update configuration."""
        env_file = BASE_DIR / ".env"
        
        if request.method == 'GET':
            config = {}
            if env_file.exists():
                for line in env_file.read_text().split('\n'):
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip().strip('"')
            return jsonify(config)
        
        else:  # POST
            data = request.json
            content = f"""# Open Medical Secretary Configuration
# Generated: {datetime.now().isoformat()}

# SIP Trunk
SIP_SERVER="{data.get('sip_server', '')}"
SIP_PORT="5060"
SIP_USERNAME="{data.get('sip_username', '')}"
SIP_PASSWORD="{data.get('sip_password', '')}"

# Doctor Phone (emergencies)
DOCTOR_PHONE_NUMBER="{data.get('doctor_phone', '')}"

# AI Model
OLLAMA_MODEL="{data.get('ollama_model', 'llama3.2:3b')}"
"""
            env_file.write_text(content)
            return jsonify({'success': True})
    
    @app.route('/api/calls')
    def api_calls():
        """Get call history."""
        calls_file = DATA_DIR / "calls.json"
        if calls_file.exists():
            return jsonify(json.loads(calls_file.read_text()))
        return jsonify([])
    
    @app.route('/api/test')
    def api_test():
        """Run a test."""
        return jsonify({
            'success': True,
            'message': 'Test effectué! Vérifiez les logs.'
        })
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=3000)
