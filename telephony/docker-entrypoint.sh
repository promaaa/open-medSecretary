#!/bin/bash
# =============================================================================
# Asterisk Docker Entrypoint
# =============================================================================
# Generates configuration from templates using environment variables
# =============================================================================

set -e

echo "🔧 Configuring Asterisk..."

# Default values
export SIP_SERVER=${SIP_SERVER:-"siptrunk.ovh.net"}
export SIP_PORT=${SIP_PORT:-"5060"}
export SIP_USERNAME=${SIP_USERNAME:-""}
export SIP_PASSWORD=${SIP_PASSWORD:-""}
export AUDIOSOCKET_HOST=${AUDIOSOCKET_HOST:-"host.docker.internal"}
export AUDIOSOCKET_PORT=${AUDIOSOCKET_PORT:-"9001"}

# Check required variables
if [ -z "$SIP_USERNAME" ] || [ -z "$SIP_PASSWORD" ]; then
    echo "⚠️  SIP_USERNAME and SIP_PASSWORD not set"
    echo "   Asterisk will start but SIP trunk won't work"
    echo "   Set these in your .env file or docker-compose.yml"
fi

# Generate pjsip.conf from template
echo "📝 Generating pjsip.conf..."
envsubst < /etc/asterisk/templates/pjsip.conf.template > /etc/asterisk/pjsip.conf

# Update extensions.conf with AudioSocket host
sed -i "s/host.docker.internal/${AUDIOSOCKET_HOST}/g" /etc/asterisk/extensions.conf
sed -i "s/9001/${AUDIOSOCKET_PORT}/g" /etc/asterisk/extensions.conf

echo "✅ Configuration complete!"
echo ""
echo "📞 SIP Server: ${SIP_SERVER}:${SIP_PORT}"
echo "🤖 AudioSocket: ${AUDIOSOCKET_HOST}:${AUDIOSOCKET_PORT}"
echo ""

# Execute the main command
exec "$@"
