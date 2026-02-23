# Zeus MyAADE Monitor - Deployment Guide

> Complete deployment instructions for the automated MyAADE protocol monitoring system.
> Part of the **Justice for John** automation framework.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (One Command)](#quick-start-one-command)
3. [Manual Setup](#manual-setup)
4. [Configuration Reference](#configuration-reference)
5. [Docker Architecture](#docker-architecture)
6. [Monitoring & Logs](#monitoring--logs)
7. [Troubleshooting](#troubleshooting)
8. [Security Notes](#security-notes)
9. [Maintenance](#maintenance)

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Linux/macOS/WSL2 | Ubuntu 22.04+ |
| RAM | 1 GB free | 2 GB free |
| Disk | 500 MB | 1 GB |
| Docker | 20.10+ | 24.0+ |
| Docker Compose | v2.0+ | v2.20+ |

### Required Credentials

Before deployment, you need:

- **MyAADE/TaxisNet username** (your TAXISnet login)
- **MyAADE/TaxisNet password**
- **TaxisNet code** (optional, for enhanced access)
- **Webhook URL** (Slack, Discord, or generic - at least one recommended)

### Install Docker (if needed)

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker compose version
```

---

## Quick Start (One Command)

The fastest way to deploy Zeus MyAADE Monitor:

```bash
# 1. Clone the repository
git clone https://github.com/alexandros-thomson/zeus-myaade-monitor.git
cd zeus-myaade-monitor

# 2. Run the deployment script
chmod +x deploy.sh
./deploy.sh
```

The `deploy.sh` script will:
1. Check all prerequisites (Docker, Docker Compose, git)
2. Create `.env` from `.env.example` if it doesn't exist
3. Prompt you to configure credentials
4. Create data directories (`data/`, `screenshots/`, `logs/`)
5. Stop any existing containers
6. Build the Docker image
7. Start the monitor in detached mode

---

## Manual Setup

If you prefer step-by-step control:

### Step 1: Clone & Configure

```bash
git clone https://github.com/alexandros-thomson/zeus-myaade-monitor.git
cd zeus-myaade-monitor

# Create your environment file
cp .env.example .env
```

### Step 2: Edit Credentials

Open `.env` in your editor and fill in your credentials:

```bash
nano .env
```

**Required fields:**
```
MYAADE_USERNAME=your_taxisnet_username
MYAADE_PASSWORD=your_taxisnet_password
```

**Recommended fields:**
```
# At least one notification webhook
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK/URL
WEBHOOK_URL=https://your-generic-webhook.com/endpoint
```

### Step 3: Create Data Directories

```bash
mkdir -p data screenshots logs
```

### Step 4: Build & Launch

```bash
# Build the Docker image
docker compose build

# Start in detached mode
docker compose up -d
```

### Step 5: Verify

```bash
# Check container status
docker compose ps

# View live logs
docker compose logs -f
```

---

## Configuration Reference

All configuration is managed through environment variables in the `.env` file.

### Credentials

| Variable | Required | Description |
|----------|----------|-------------|
| `MYAADE_USERNAME` | Yes | Your TaxisNet username |
| `MYAADE_PASSWORD` | Yes | Your TaxisNet password |
| `MYAADE_TAXISNET_CODE` | No | Additional TaxisNet verification code |

### Notification Webhooks

| Variable | Default | Description |
|----------|---------|-------------|
| `SLACK_WEBHOOK_URL` | (empty) | Slack incoming webhook URL |
| `DISCORD_WEBHOOK_URL` | (empty) | Discord webhook URL |
| `WEBHOOK_URL` | (empty) | Generic HTTP webhook endpoint |

At least one webhook is recommended to receive alerts.

### Monitoring Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `CHECK_INTERVAL_SECONDS` | `300` | Seconds between checks (5 min default) |
| `HEADLESS_MODE` | `true` | Run Chrome in headless mode |
| `TRACKED_PROTOCOLS` | `214142` | Comma-separated protocol numbers to track |
| `TRACK_ALL_PROTOCOLS` | `true` | Track all protocols in your account |
| `MAX_RETRIES` | `3` | Max retry attempts on failure |
| `RETRY_DELAY` | `60` | Seconds between retries |

### Resource Limits (docker-compose.yml)

| Resource | Limit | Reservation |
|----------|-------|-------------|
| CPU | 2 cores | 0.5 cores |
| Memory | 2 GB | 512 MB |

---

## Docker Architecture

### Container Structure

```
zeus-myaade-monitor/
|-- Dockerfile              # Python 3.11-slim + Chromium
|-- docker-compose.yml      # Service definition & volumes
|-- myaade_monitor_zeus.py  # Core monitoring engine
|-- requirements.txt        # Python dependencies
|-- .env.example            # Configuration template
|-- .env                    # Your credentials (gitignored)
|-- deploy.sh               # One-command deployment
|-- data/                   # SQLite database (persistent)
|-- screenshots/            # Status screenshots (persistent)
|-- logs/                   # Application logs (persistent)
```

### Volume Mounts

| Host Path | Container Path | Purpose |
|-----------|---------------|----------|
| `./data` | `/app/data` | SQLite database (`myaade_monitor.db`) |
| `./screenshots` | `/app/screenshots` | Screenshot captures |
| `./logs` | `/app/logs` | Application log files |

### Health Check

The container includes a built-in health check that verifies database connectivity every 5 minutes.

---

## Monitoring & Logs

### View Live Logs

```bash
# Follow all logs
docker compose logs -f

# Last 100 lines
docker compose logs --tail=100

# Filter by time
docker compose logs --since="2024-01-01T00:00:00"
```

### Check Container Status

```bash
# Container health and uptime
docker compose ps

# Resource usage
docker stats zeus-myaade-monitor
```

### Database Inspection

The monitoring data is stored in SQLite:

```bash
# Access the database
sqlite3 ./data/myaade_monitor.db

# View recent checks
SELECT * FROM status_checks ORDER BY checked_at DESC LIMIT 10;

# View detected deflections
SELECT * FROM deflections ORDER BY detected_at DESC;

# View all tracked protocols
SELECT * FROM protocols;
```

### Screenshots

Every status check captures a screenshot saved in `./screenshots/`. These serve as evidence of MyAADE portal states at each check time.

---

## Troubleshooting

### Container Won't Start

```bash
# Check build errors
docker compose build --no-cache

# Check logs for startup errors
docker compose logs

# Verify .env file exists and has credentials
cat .env | grep MYAADE_USERNAME
```

### Login Failures

| Symptom | Cause | Solution |
|---------|-------|----------|
| "Login failed" in logs | Wrong credentials | Verify `.env` credentials match TaxisNet |
| Timeout on login | TaxisNet portal down | Check https://myaade.gov.gr manually |
| CAPTCHA detected | Bot detection triggered | Increase `CHECK_INTERVAL_SECONDS` to 600+ |
| Session expired | Long idle period | Monitor will auto-retry |

### Chrome/Chromium Issues

```bash
# Verify Chrome is installed in container
docker compose exec myaade-monitor chromium --version

# Check shared memory (common Docker issue)
# Add to docker-compose.yml if needed:
#   shm_size: '2gb'
```

### Permission Errors

```bash
# Fix data directory permissions
sudo chown -R $USER:$USER data/ screenshots/ logs/
chmod -R 755 data/ screenshots/ logs/
```

### High Memory Usage

Chromium can be memory-intensive. If the container is being OOM-killed:

```bash
# Increase memory limit in docker-compose.yml
# Under deploy.resources.limits:
memory: 4G
```

---

## Security Notes

### Credential Protection

- The `.env` file is listed in `.gitignore` and will NOT be committed
- Never share your `.env` file or commit it to version control
- Use strong, unique passwords for your TaxisNet account
- Consider rotating webhook URLs periodically

### Container Security

- Container runs with `no-new-privileges` security option
- Log rotation is configured (10MB max, 3 files)
- Container auto-restarts on failure (`unless-stopped`)
- Resource limits prevent runaway consumption

### Network Security

- All connections to MyAADE use HTTPS
- Webhook notifications are sent over HTTPS
- No ports are exposed from the container to the host

---

## Maintenance

### Update the Monitor

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Backup Data

```bash
# Backup database and screenshots
tar -czf zeus-backup-$(date +%Y%m%d).tar.gz data/ screenshots/ logs/
```

### Clean Up

```bash
# Stop and remove container
docker compose down

# Remove Docker image
docker rmi zeus-myaade-monitor

# Remove data (CAUTION: deletes all monitoring history)
rm -rf data/ screenshots/ logs/
```

### Common Operations

| Task | Command |
|------|---------|
| Start monitor | `docker compose up -d` |
| Stop monitor | `docker compose down` |
| View logs | `docker compose logs -f` |
| Check status | `docker compose ps` |
| Restart | `docker compose restart` |
| Rebuild | `docker compose build --no-cache` |
| Shell access | `docker compose exec myaade-monitor /bin/bash` |

---

## Support

This is part of the **Justice for John** automation framework.

- Repository: [zeus-myaade-monitor](https://github.com/alexandros-thomson/zeus-myaade-monitor)
- Related: [justice-for-john-automation](https://github.com/alexandros-thomson/justice-for-john-automation)

---

*The PHAYLOS KYKLOS ends TODAY. Justice for John.*
