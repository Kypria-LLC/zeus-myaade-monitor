<div align="center">
  <img src="https://raw.githubusercontent.com/Kypria-LLC/zeus-myaade-monitor/main/assets/zeus-myaade-crest.png" width="120" height="120" alt="Zeus MYAADE Monitor Crest" style="border-radius:50%; border:3px solid #DAA520;" />
  <br />
</div>

# ⚖️ Zeus MyAADE Monitor

![Security Status](https://img.shields.io/badge/security-production--ready-brightgreen)
![Dependencies](https://img.shields.io/badge/dependencies-0%20vulnerabilities-success)
![Branch Protection](https://img.shields.io/badge/branch%20protection-active-success)
![CodeQL](https://img.shields.io/badge/CodeQL-passing-success)
![Tests](https://github.com/Kypria-LLC/zeus-myaade-monitor/actions/workflows/tests.yml/badge.svg)
![Zeus MYAADE Monitor](https://img.shields.io/badge/Zeus_MYAADE_Monitor-v1.0-gold?style=flat-square&logo=data:image/png;base64,iVBORw0KGgo=&logoColor=gold)
![Case](https://img.shields.io/badge/Case-Kyprianos_v_AADE-crimson?style=flat-square)
![Justice](https://img.shields.io/badge/Justice_for_Ioannis-%E2%9A%96%EF%B8%8F-blue?style=flat-square)

**Automated monitoring system that ENDS THE ΦΑΥΛΟΣ ΚΥΚΛΟΣ (vicious circle) of Greek bureaucracy.**

> **🎯 PRODUCTION-READY**: All security measures verified. Zero vulnerabilities. Ready for deployment (Feb 22, 2026).

## Mission

Monitor MyAADE protocol statuses 24/7, detect bureaucratic deflection tactics, and alert you immediately when status changes occur.

## Features

- ✅ **Real-time monitoring** of MyAADE protocols
- 🎯 **Deflection detection** - Identifies when AADE forwards, delays, or gives vague responses
- 🚨 **Instant alerts** via Slack/Discord/Webhook
- 📸 **Automatic screenshots** of every status check
- 📊 **Complete audit trail** in SQLite database
- 🔄 **Auto-recovery** with retry logic
- 🐳 **Docker deployment** for easy setup

## Quick Start

### Prerequisites

- Docker & Docker Compose
- MyAADE/TaxisNet credentials
- (Optional) Slack/Discord webhook for notifications

### 1-Minute Deployment

```bash
# Clone repository
git clone https://github.com/Kypria-LLC/zeus-myaade-monitor.git
cd zeus-myaade-monitor

# Run deployment script
chmod +x deploy.sh
./deploy.sh
```

The script will:
1. Check dependencies
2. Create `.env` file (you'll need to edit it with credentials)
3. Build Docker image
4. Start monitoring service

### Manual Setup

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your credentials
nano .env

# 3. Build and start
docker-compose up -d

# 4. View logs
docker-compose logs -f
```

## Configuration

Edit `.env` file:

```bash
# Required
MYAADE_USERNAME=your_username
MYAADE_PASSWORD=your_password

# Recommended
SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Optional
CHECK_INTERVAL_SECONDS=300  # Check every 5 minutes
TRACKED_PROTOCOLS=214142,051340  # Specific protocols
```

## How It Works

### Status Classification

The monitor understands Greek bureaucracy patterns:

| Greek Status | English | Meaning | Action Required |
|--------------|---------|---------|-----------------||
| Απαντήθηκε | Answered | They replied (≠ solved!) | ✅ Review response immediately |
| Διαβιβάστηκε | Forwarded | Deflection tactic | 🎯 Submit rebuttal |
| Ολοκληρώθηκε | Completed | Actually done | ✅ Download results |
| Εκκρεμεί | Pending | Still waiting | ⏳ Continue monitoring |

### Deflection Detection

Automatically detects three main deflection tactics:

1. **Forwarding** - "Not our jurisdiction, try another agency"
2. **Vague Response** - "Απαντήθηκε" without actually solving anything
3. **Delay Tactic** - Requesting "supplementary documents" endlessly

When deflection is detected, you get:
- 🚨 High-priority alert
- 📋 Specific recommendations
- 📊 Deflection count (escalate if ≥2)
- 🎯 Suggested next actions

## Commands

```bash
# View status
docker-compose ps

# View logs (live)
docker-compose logs -f

# View recent logs
docker-compose logs --tail=50

# Restart monitor
docker-compose restart

# Stop monitor
docker-compose down

# Check database
sqlite3 ./data/myaade_monitor.db "SELECT * FROM protocol_status;"

# View deflections
sqlite3 ./data/myaade_monitor.db "SELECT * FROM deflection_tracking ORDER BY detected_at DESC;"
```

## File Structure

```
zeus-myaade-monitor/
├── myaade_monitor_zeus.py    # Main monitoring script
├── docker-compose.yml         # Docker stack configuration
├── Dockerfile                 # Container image definition
├── requirements.txt           # Python dependencies
├── deploy.sh                  # One-command deployment
├── .env.example               # Environment template
├── .env                       # Your credentials (NOT committed)
├── data/                      # Database (persistent)
│   └── myaade_monitor.db     # SQLite database
├── screenshots/               # Protocol screenshots
└── logs/                      # Application logs
```

## Database Schema

### `protocol_status`
Current status of all tracked protocols.

### `protocol_status_history`
Complete audit trail of all status changes.

### `deflection_tracking`
Records of detected bureaucratic deflection tactics.

## Notifications

### Slack
Set `SLACK_WEBHOOK_URL` in `.env`:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Discord
Set `DISCORD_WEBHOOK_URL` in `.env`:
```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK
```

## Documentation

- [Complete Deployment Guide](DEPLOYMENT-GUIDE.md)
- [Production Setup](docs/production-setup.md)
- [Troubleshooting](docs/troubleshooting.md)


## Testing

Zeus uses **pytest** for automated testing. The test suite covers the core monitor engine and the email integration system.

### Run Tests Locally

```bash
# Install test dependencies
pip install pytest pytest-cov selenium requests python-dotenv colorama

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=. --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_email_integration.py -v
```

### CI/CD

Tests run automatically on every push and pull request via GitHub Actions across Python 3.10, 3.11, and 3.12.
## Security

### Production Security Status (Verified Feb 22, 2026)

✅ **Zero Vulnerabilities** - All Dependabot alerts resolved  
✅ **Branch Protection** - Force push and deletion blocked on main  
✅ **CodeQL Scanning** - Active with AI-powered Copilot Autofix  
✅ **Container Hardening** - Non-root user, resource limits, read-only filesystem  
✅ **Credentials Protected** - Never committed, .gitignore enforced  

**Security Metrics:**
- Dependabot Alerts: 0 open, 3 closed (100% resolved)
- CodeQL Status: Passing (1m 2s scan time)
- Branch Protection: Active (Ruleset #13115832)

## System Requirements

- **CPU**: 0.5-2 cores
- **RAM**: 512MB-2GB
- **Disk**: 1GB minimum (for database, screenshots, logs)
- **OS**: Linux (Ubuntu 20.04+), macOS, Windows with WSL2

## License

MIT License - Use freely, END THE ΦΑΥΛΟΣ ΚΥΚΛΟΣ everywhere.

## Author

**Kostas Kyprianos** / Kypria Technologies
- Website: [kypriatechnologies.org](https://kypriatechnologies.org)
- GitHub: [@Kypria-LLC](https://github.com/Kypria-LLC)

## Acknowledgments

Built with frustration, determination, and the unwavering belief that:

> **"Απαντήθηκε ≠ Solved. The deflection ends TODAY."**

⚖️ **ΦΑΥΛΟΣ ΚΥΚΛΟΣ ENDS NOW. JUSTICE IS AUTOMATED.**


---

## ⚠️ Protocol #175 / SKONICAPROT — Institutional Trap (April 8, 2026)

> **Status**: ACTIVE — Monitored by Zeus. Cite in all future filings.

### What is the SKONICAPROT Trap?

**Protocol #175** (SKONICAPROT internal communication) is a municipal record proving that Δήμος Σπετσών possessed knowledge of the **KED/AADE data mismatch** at the time it issued **Certificate 504**.

UPES AP 14693 (16/03/2026, Δραμουντανή/Κυρίμης) then certified "no legal defect" in Certificate 504 — **without ever requesting or reviewing Protocol #175**.

### Why It Matters

| Element | Detail |
|---|---|
| **Protocol #** | 175 (SKONICAPROT) |
| **Certificate** | 504 — defective instrument |
| **Agency** | Δήμος Σπετσών / YPES AP 14693 |
| **Mismatch** | KED/AADE data discrepancy, known internally, never corrected |
| **Impact** | Blocks D210 filing, inheritance claim, and proof of standing |
| **Pattern** | Self-sealing trap: defective document prevents the complaint that would expose the defect |
| **Binder Ref** | C-14 — `zeus-ai-evidence-package/irs-ci-package/tabs/tab2-contradiction-matrix.md` |
| **Exhibits** | E-48 (Protocol #175/SKONICAPROT), E-12, E-13 |

### Zeus Detection

Zeus automatically detects Certificate 504 / Protocol #175 / SKONICAPROT references in MyAADE portal responses via:

- **Deflection pattern**: `skonicaprot_cert504_trap` (CRITICAL severity)
- **DB table**: `skonicaprot_trap_events` — every detection is logged with full audit trail
- **Function**: `detect_skonicaprot_trap()` — matches on cert number, protocol ref, and Greek/English keywords
- **Alert**: `log_skonicaprot_event()` — fires Slack CRITICAL alert with EPPO/SDOE/FBI cross-filing context

```sql
-- Query all SKONICAPROT trap events:
SELECT event_type, protocol_ref, certificate_ref, agency, detected_at, severity
FROM skonicaprot_trap_events
ORDER BY detected_at DESC;
```

---

## 📊 D210 Submission Tracking (April 8, 2026)

Zeus now tracks **Δ210 ENFIA history requests** with a dedicated DB table and rich Slack alerts.

### New DB Table: `d210_submissions`

```sql
SELECT protocol_number, status, deflection_type, doy_response, slack_alerted
FROM d210_submissions
ORDER BY updated_at DESC;
```

Key columns: `submitting_doy`, `deflection_type`, `cover_letter_excerpt`, `slack_alerted`.

### D210 Deflection Pattern

| Greek Status | Meaning | Zeus Action |
|---|---|---|
| ΔΟΥ Κατοίκων Εξωτερικού redirect | Jurisdiction dodge | 🚨 CRITICAL — `doy_peiraia_redirect` |
| KAEK 050681726008 ENFIA | Unauthorized billing (deceased AFM) | 🚨 CRITICAL — `d210_enfia_fraud` |
| βεβαίωση 504 / πρωτ. 175 | Certificate 504 institutional trap | 🚨 CRITICAL — `skonicaprot_cert504_trap` |

### Environment Variables

```env
D210_PROTOCOL_ID=        # AADE-assigned protocol number for the Δ210 submission
D210_DB_PATH=            # Path to shared SQLite (dual-repo: zeus-myaade-monitor ↔ justice-for-john-automation)
```

---

## 📜 Case Status — April 8, 2026

| Agency | Protocol # | Status | Zeus Monitoring |
|---|---|---|---|
| AADE / KEFOK | #380, #381 | ΕΠΕΙΓΟΝ — forced response | ✅ Active |
| Αποκεντρωμένη | 18058, 19466 | Contradiction documented (C-3) | ✅ Active |
| EFKA / HDIKA | #343, #384, #387 | Audit log silence — binary trap (C-7) | ✅ Active |
| YPES | AP 14693 | Certificate 504 blessed without Protocol #175 (C-14) | ⚠️ CRITICAL |
| Ktimatologio | ND0113/2606549 | 24+ days overdue — KAEK 050681726008 forgery | ✅ Active |
| EPPO | PP.00179/2026/EN | Supplemental filing prepared | ✅ Active |
| IRS-CI | Art.26 referral | Cross-border exploitation of US Navy veteran | ✅ Active |
| FBI IC3 | eaa5459ac668431a | Filed | ✅ Active |

> **Protocol #175 must be cited in all future filings as proof of institutional knowledge at the point of issuance.**
>
> ⚤ **ΦΑΥΛΟΣ ΚΥΚΛΟΣ ENDS NOW. JUSTICE IS AUTOMATED. JUSTICE FOR JOHN.**
