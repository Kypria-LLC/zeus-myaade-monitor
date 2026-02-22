# ═══════════════════════════════════════════════════════════════════════════
# ZEUS MYAADE MONITOR - PRODUCTION DOCKERFILE
# ═══════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome/ChromeDriver environment variables
ENV CHROME_BINARY=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY myaade_monitor_zeus.py .

# Create data directories
RUN mkdir -p /app/data /app/screenshots /app/logs

# Set permissions
RUN chmod +x myaade_monitor_zeus.py

# Health check
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sqlite3; conn = sqlite3.connect('/app/data/myaade_monitor.db'); conn.close()" || exit 1

# Run the monitor
CMD ["python", "-u", "myaade_monitor_zeus.py"]