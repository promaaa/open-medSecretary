# =============================================================================
# Asterisk PBX for Open Medical Secretary
# =============================================================================
# Pre-configured for SIP trunk integration with AI voice assistant
# =============================================================================

FROM debian:bookworm-slim

# Install Asterisk and dependencies
RUN apt-get update && apt-get install -y \
    asterisk \
    asterisk-core-sounds-fr-wav \
    asterisk-core-sounds-fr-g722 \
    asterisk-moh-opsound-wav \
    gettext-base \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /etc/asterisk/templates

# Copy configuration templates
COPY config/pjsip.conf.template /etc/asterisk/templates/
COPY config/extensions.conf /etc/asterisk/extensions.conf
COPY config/asterisk.conf /etc/asterisk/asterisk.conf
COPY config/modules.conf /etc/asterisk/modules.conf
COPY config/rtp.conf /etc/asterisk/rtp.conf

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose ports
# SIP signaling
EXPOSE 5060/udp
EXPOSE 5060/tcp
# RTP media (audio)
EXPOSE 10000-10100/udp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD asterisk -rx "core show channels" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["asterisk", "-fvvv"]
