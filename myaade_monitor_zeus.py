#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
# CI gate job added to satisfy branch protection required status check
myaade_monitor_zeus.py -- Zeus MyAADE Protocol Monitor

Selenium-based 24/7 monitoring system for the MyAADE (AADE TaxisNet) portal.
Detects bureaucratic deflection patterns, tracks protocol statuses,
captures evidence screenshots, and sends instant alerts.

Part of the Justice for John Automation System.
Case: EPPO PP.00179/2026/EN | FBI IC3 | IRS CI Art. 26

Author: Kostas Kyprianos / Kypria Technologies
Date: February 25, 2026 (Updated April 8, 2026)
License: MIT
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import signal
import sqlite3
import sys
import time
import traceback
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException,
        WebDriverException, StaleElementReferenceException,
    )
except ImportError:
    print("FATAL: selenium not installed. Run: pip install selenium")
    sys.exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("FATAL: webdriver-manager not installed. Run: pip install webdriver-manager")
    sys.exit(1)

try:
    import requests
except ImportError:
    requests = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init()
except ImportError:
    class Fore:
        RED = GREEN = YELLOW = CYAN = MAGENTA = WHITE = RESET = ""
    class Style:
        BRIGHT = RESET_ALL = ""

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("zeus-monitor")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
class Config:
    """Configuration loaded from environment variables."""
    MYAADE_USERNAME: str = os.getenv("MYAADE_USERNAME", "")
    MYAADE_PASSWORD: str = os.getenv("MYAADE_PASSWORD", "")
    MYAADE_TAXISNET_CODE: str = os.getenv("MYAADE_TAXISNET_CODE", "")

    # Monitoring intervals
    CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY_SECONDS", "60"))

    # Browser config
    HEADLESS: bool = os.getenv("HEADLESS_MODE", "true").lower() not in ["false", "0", "no"]
    CHROME_BINARY: str = os.getenv("CHROME_BINARY", "")

    # Protocol tracking
    TRACKED_PROTOCOLS: List[str] = [
        p.strip() for p in os.getenv("TRACKED_PROTOCOLS", "214142").split(",")
        if p.strip()
    ]
    TRACK_ALL: bool = os.getenv("TRACK_ALL_PROTOCOLS", "true").lower() == "true"

    # Notification webhooks
    SLACK_WEBHOOK: str = os.getenv("SLACK_WEBHOOK_URL", "")
    DISCORD_WEBHOOK: str = os.getenv("DISCORD_WEBHOOK_URL", "")
    GENERIC_WEBHOOK: str = os.getenv("WEBHOOK_URL", "")

    # Paths (container paths by default)
    DB_PATH: Path = Path(os.getenv("MYAADE_DB_PATH", "/app/data/myaade_monitor.db"))
    SCREENSHOT_DIR: Path = Path(os.getenv("SCREENSHOT_DIR", "/app/screenshots"))
    LOG_DIR: Path = Path(os.getenv("LOG_DIR", "/app/logs"))

    # AFMs to monitor
    AFM_STAMATINA: str = "044594747"
    AFM_JOHN_DECEASED: str = "051422558"

    # MyAADE URLs -- GSIS OAuth login portal
    MYAADE_BASE: str = "https://www1.aade.gr/taxisnet"
    MYAADE_LOGIN_ENTRY: str = "https://www1.aade.gr/taxisnet/mytaxisnet"
    MYAADE_INBOX: str = "https://www1.aade.gr/taxisnet/mymessages/protected/inbox.htm"
    MYAADE_VIEW_MESSAGE: str = "https://www1.aade.gr/taxisnet/mymessages/protected/viewMessage.htm"
    MYAADE_APPLICATIONS: str = "https://www1.aade.gr/taxisnet/mytaxisnet/protected/applications.htm"

    # Critical Deadlines
    DEADLINE_MINDIGITAL: date = date(2026, 3, 6)
    MINDIGITAL_PROTOCOLS: List[str] = ["4633", "4505", "4314"]

    # 03/03 EAD Statutory Strike Recipients
    STRIKE_TO = ["grammateia@aead.gr", "dms@aead.gr"]
    STRIKE_CC_DOMESTIC = ["ccu@cybercrimeunit.gov.gr", "desyp@aade.gr", "complaints@synigoros.gr"]
    STRIKE_CC_INTL = ["info@eppo.europa.eu", "luxembourg@eppo.europa.eu", "DetroitFieldOffice@ci.irs.gov", "athens.legat@ic.fbi.gov"]

config = Config()

# ---------------------------------------------------------------------------
# Deflection Detection Patterns
# ---------------------------------------------------------------------------
DEFLECTION_PATTERNS = {
    "doy_peiraia_redirect": {
        "keywords_el": ["δου κατοίκων εξωτερικού", "αρμόδια δου εξωτερικού", "κατοίκων εξωτερικού"],
        "keywords_en": ["foreign residents tax office", "competent doy for foreigners"],
        "severity": "CRITICAL",
        "description": "Jurisdictional deflection pattern (Peiraia -> Foreign Residents)",
    },
    "forwarded": {
        "keywords_el": ["διαβιβάστηκε", "προωθήθηκε", "αρμόδια υπηρεσία"],
        "keywords_en": ["forwarded", "referred to", "competent authority"],
        "severity": "HIGH",
        "description": "Protocol forwarded to another agency (deflection)",
    },
    "under_review": {
        "keywords_el": ["εξετάζεται", "υπό επεξεργασία", "σε εξέλιξη"],
        "keywords_en": ["under review", "processing", "in progress"],
        "severity": "WATCH",
        "description": "Generic 'under review' status (possible stalling)",
    },
    "no_jurisdiction": {
        "keywords_el": ["αναρμόδιο", "δεν υπάγεται", "δεν εμπίπτει"],
        "keywords_en": ["no jurisdiction", "not competent", "outside scope"],
        "severity": "CRITICAL",
        "description": "Agency claims no jurisdiction (hard deflection)",
    },
    "responded": {
        "keywords_el": ["απαντήθηκε", "ολοκληρώθηκε", "διεκπεραιώθηκε"],
        "keywords_en": ["answered", "completed", "resolved"],
        "severity": "CRITICAL",
        "description": "Marked as 'answered' -- verify actual resolution",
    },
    "archived": {
        "keywords_el": ["αρχειοθετήθηκε", "τέθηκε στο αρχείο"],
        "keywords_en": ["archived", "filed away"],
        "severity": "CRITICAL",
        "description": "Protocol archived without resolution",
    },
        "skonicaprot_cert504_trap": {
        "keywords_el": ["βεβαίωση 504", "πρωτ. 175", "σκονικαπροτ", "ked/aade", "δεν διαπιστώνεται"],
        "keywords_en": ["certificate 504", "protocol 175", "skonicaprot", "no legal defect", "ked/aade mismatch"],
        "severity": "CRITICAL",
        "description": "Certificate 504 institutional trap (Protocol #175/SKONICAPROT) -- municipality issued with known KED/AADE mismatch. Blocks D210, inheritance, and legal standing. Cite Protocol #175 in all future filings.",
    },
    "d210_enfia_fraud": {
        "keywords_el": ["δ210", "δ211", "ενφια", "φανταστική επιχείρηση", "kaek 050681726008"],
        "keywords_en": ["d210", "d211", "enfia", "phantom business", "unauthorized enfia"],
        "severity": "CRITICAL",
        "description": "D210/D211 submission blocked or ENFIA billed against deceased AFM 051422558 or KAEK 050681726008 (Keratsini). Cross-file: EPPO/SDOE/IRS-CI.",
    },
}

def _norm(s: str) -> str:
    """Normalize Greek text by removing accents and converting to lowercase."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.casefold())
        if unicodedata.category(c) != "Mn"
    )

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class ProtocolStatus:
    """Snapshot of a protocol's status at a point in time."""
    protocol_number: str
    status_text: str = ""
    status_date: str = ""
    agency: str = ""
    subject: str = ""
    response_text: str = ""
    deflection_type: Optional[str] = None
    deflection_severity: Optional[str] = None
    screenshot_path: Optional[str] = None
    screenshot_hash: Optional[str] = None
    page_source_hash: Optional[str] = None
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_html_length: int = 0
    changed: bool = False

# ---------------------------------------------------------------------------
# Database Layer -- SQLite with WAL mode
# ---------------------------------------------------------------------------
CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS protocol_checks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_number TEXT NOT NULL,
    status_text     TEXT,
    status_date     TEXT,
    agency          TEXT,
    subject         TEXT,
    response_text   TEXT,
    deflection_type TEXT,
    deflection_severity TEXT,
    screenshot_path TEXT,
    screenshot_hash TEXT,
    page_source_hash TEXT,
    checked_at      TEXT NOT NULL,
    raw_html_length INTEGER DEFAULT 0,
    changed         INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_number TEXT NOT NULL,
    alert_type      TEXT NOT NULL,
    severity        TEXT NOT NULL,
    message         TEXT NOT NULL,
    details         TEXT,
    sent_slack      INTEGER DEFAULT 0,
    sent_discord    INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monitor_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    protocols_checked INTEGER DEFAULT 0,
    alerts_generated INTEGER DEFAULT 0,
    errors          INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'running'
);

CREATE INDEX IF NOT EXISTS idx_checks_protocol
    ON protocol_checks(protocol_number);
CREATE INDEX IF NOT EXISTS idx_checks_time
    ON protocol_checks(checked_at);
CREATE INDEX IF NOT EXISTS idx_alerts_protocol
    ON alerts(protocol_number);
"""

def init_database(db_path: Path) -> sqlite3.Connection:
    """Initialize SQLite database with WAL mode."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(CREATE_SCHEMA_SQL)
    conn.commit()
    logger.info("Database initialized: %s", db_path)
    return conn

# ---------------------------------------------------------------------------
# Screenshot & Evidence Capture
# ---------------------------------------------------------------------------
def capture_screenshot(driver, protocol_num: str, screenshot_dir: Path) -> tuple[Optional[str], Optional[str]]:
    """Capture a screenshot and return (path, sha256_hash)."""
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"protocol_{protocol_num}_{ts}.png"
    filepath = screenshot_dir / filename
    try:
        driver.save_screenshot(str(filepath))
        with open(filepath, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        logger.info("Screenshot saved: %s (SHA256: %s)", filename, file_hash[:16])
        return str(filepath), file_hash
    except Exception as e:
        logger.error("Screenshot failed for %s: %s", protocol_num, e)
        return None, None

def capture_html_error(driver, error_type: str, screenshot_dir: Path) -> str:
    """Capture the full HTML of an error page for diagnosis."""
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"error_{error_type}_{ts}.html"
    filepath = screenshot_dir / filename
    try:
        page_source = driver.page_source
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"""<!DOCTYPE html>
<html>
<head>
    <title>Error Capture: {error_type}</title>
    <meta charset=\"utf-8\">
    <meta name=\"captured_at\" content=\"{datetime.now(timezone.utc).isoformat()}\">
    <meta name=\"current_url\" content=\"{driver.current_url}\">
    <meta name=\"page_title\" content=\"{driver.title}\">
</head>
<body>
    <h1>Error Capture Report</h1>
    <ul>
        <li><strong>Error Type:</strong> {error_type}</li>
        <li><strong>URL:</strong> {driver.current_url}</li>
        <li><strong>Page Title:</strong> {driver.title}</li>
        <li><strong>Captured:</strong> {datetime.now(timezone.utc).isoformat()}</li>
    </ul>
    <hr>
    <h2>Page Source:</h2>
    <pre>{page_source}</pre>
</body>
</html>""")
        logger.info("Error HTML saved: %s", filename)
        return str(filepath)
    except Exception as e:
        logger.error("Failed to capture error HTML: %s", e)
        return ""

# ---------------------------------------------------------------------------
# Deflection Analysis Engine
# ---------------------------------------------------------------------------
def analyze_deflection(text: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Analyze text for deflection patterns. Returns (type, severity, description)."""
    text_norm = _norm(text)
    for pattern_name, pattern in DEFLECTION_PATTERNS.items():
        for keyword in pattern["keywords_el"] + pattern["keywords_en"]:
            norm_kw = _norm(keyword)
            if norm_kw and norm_kw in text_norm:
                return pattern_name, pattern["severity"], pattern["description"]
    return None, None, None

# ---------------------------------------------------------------------------
# Notification System
# ---------------------------------------------------------------------------
def send_slack_alert(webhook_url: str, message: str, severity: str = "INFO", attachments: Optional[List[Dict[str, Any]]] = None) -> bool:
    """Send an alert to Slack via webhook."""
    if not webhook_url or not requests:
        return False
    color_map = {"CRITICAL": "#FF0000", "HIGH": "#FF6600", "WATCH": "#FFCC00", "INFO": "#0066FF"}
    
    payload = {
        "attachments": attachments or [{
            "color": color_map.get(severity, "#808080"),
            "title": f"Zeus Monitor Alert [{severity}]",
            "text": message,
            "footer": "Zeus MyAADE Monitor | Justice for John",
            "ts": int(time.time()),
        }]
    }
    
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error("Slack notification failed: %s", e)
        return False

def send_discord_alert(webhook_url: str, message: str, severity: str = "INFO") -> bool:
    """Send an alert to Discord via webhook."""
    if not webhook_url or not requests:
        return False
    color_map = {"CRITICAL": 0xFF0000, "HIGH": 0xFF6600, "WATCH": 0xFFCC00, "INFO": 0x0066FF}
    payload = {
        "embeds": [{
            "title": f"Zeus Monitor Alert [{severity}]",
            "description": message,
            "color": color_map.get(severity, 0x808080),
            "footer": {"text": "Zeus MyAADE Monitor | Justice for John"},
        }]
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return resp.status_code in (200, 204)
    except Exception as e:
        logger.error("Discord notification failed: %s", e)
        return False

def send_alerts(message: str, severity: str = "INFO", attachments: Optional[List[Dict[str, Any]]] = None) -> None:
    """Send alerts to all configured notification channels."""
    if config.SLACK_WEBHOOK:
        send_slack_alert(config.SLACK_WEBHOOK, message, severity, attachments)
    if config.DISCORD_WEBHOOK:
        send_discord_alert(config.DISCORD_WEBHOOK, message, severity)
    if config.GENERIC_WEBHOOK and requests:
        try:
            requests.post(config.GENERIC_WEBHOOK, json={
                "severity": severity,
                "message": message,
                "source": "zeus-myaade-monitor",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, timeout=10)
        except Exception as e:
            logger.error("Generic webhook failed: %s", e)

# ---------------------------------------------------------------------------
# Zeus Monitor -- Core Engine
# ---------------------------------------------------------------------------
class ZeusMonitor:
    """24/7 MyAADE protocol monitoring engine using Selenium."""

    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.db: Optional[sqlite3.Connection] = None
        self.running = True
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Handle graceful shutdown."""
        def _handler(signum, frame):
            logger.info("Shutdown signal received (signal %s)", signum)
            self.running = False
        signal.signal(signal.SIGINT, _handler)
        signal.signal(signal.SIGTERM, _handler)

    def _create_driver(self) -> webdriver.Chrome:
        """Create a Selenium Chrome/Chromium WebDriver."""
        options = ChromeOptions()
        if config.HEADLESS:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=el-GR")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)
        logger.info("WebDriver created (headless=%s)", config.HEADLESS)
        return driver

    def _login_taxisnet(self) -> bool:
        """Authenticate via TaxisNet OAuth (GSIS login)."""
        if not config.MYAADE_USERNAME or not config.MYAADE_PASSWORD:
            logger.error("Missing MYAADE credentials in .env")
            return False

        try:
            logger.info("Navigating to GSIS login entry page...")
            self.driver.get(config.MYAADE_LOGIN_ENTRY)
            wait = WebDriverWait(self.driver, 30)

            wait.until(EC.presence_of_element_located((By.ID, "username")))
            
            # Fill credentials
            self.driver.find_element(By.ID, "username").send_keys(config.MYAADE_USERNAME)
            self.driver.find_element(By.ID, "password").send_keys(config.MYAADE_PASSWORD)
            
            # Submit (using fallback selectors if needed)
            submit_found = False
            for selector in ["btn_login", "button[type='submit']", "input[type='submit']"]:
                try:
                    btn = self.driver.find_element(By.NAME if "btn" in selector else By.CSS_SELECTOR, selector)
                    btn.click()
                    submit_found = True
                    break
                except NoSuchElementException: continue
            
            if not submit_found: raise NoSuchElementException("Login button not found")

            # Wait for redirect
            wait.until(lambda d: "taxisnet" in d.current_url or "myaade" in d.current_url)
            logger.info("TaxisNet login successful")
            return True

        except Exception as e:
            logger.error("Login failed: %s", e)
            capture_screenshot(self.driver, "login_failed", config.SCREENSHOT_DIR)
            return False

    def _get_previous_status(self, protocol_num: str) -> Optional[str]:
        """Get the most recent page_source_hash for change detection."""
        cursor = self.db.execute(
            "SELECT page_source_hash FROM protocol_checks "
            "WHERE protocol_number = ? ORDER BY checked_at DESC LIMIT 1",
            (protocol_num,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def _save_check(self, status: ProtocolStatus) -> int:
        """Save a protocol check result to the database."""
        cursor = self.db.execute(
            """INSERT INTO protocol_checks
            (protocol_number, status_text, status_date, agency, subject,
             response_text, deflection_type, deflection_severity,
             screenshot_path, screenshot_hash, page_source_hash,
             checked_at, raw_html_length, changed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (status.protocol_number, status.status_text, status.status_date,
             status.agency, status.subject, status.response_text,
             status.deflection_type, status.deflection_severity,
             status.screenshot_path, status.screenshot_hash,
             status.page_source_hash, status.checked_at,
             status.raw_html_length, int(status.changed)),
        )
        self.db.commit()
        return cursor.lastrowid

    def _save_alert(self, protocol_num: str, alert_type: str,
                    severity: str, message: str, details: str = "") -> int:
        """Save an alert to the database."""
        cursor = self.db.execute(
            """INSERT INTO alerts
            (protocol_number, alert_type, severity, message, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (protocol_num, alert_type, severity, message, details,
             datetime.now(timezone.utc).isoformat()),
        )
        self.db.commit()
        return cursor.lastrowid

    def _check_mindigital_deadline(self, protocol_num: str, status: ProtocolStatus):
        """Check if the March 6th MinDigital deadline has been missed."""
        if protocol_num in config.MINDIGITAL_PROTOCOLS:
            today = date.today()
            if today >= config.DEADLINE_MINDIGITAL:
                # If status is still silent/pending or deflected after deadline
                if status.deflection_type or any(kw in _norm(status.status_text) for kw in ["εκκρεμει", "pending"]):
                    logger.critical("DEADLINE MISSED for MinDigital protocol %s", protocol_num)
                    
                    excerpt = (
                        "This notice documents the formal detection of a jurisdictional deflection pattern... "
                        "The system has identified a 'jurisdiction-dodge' pattern where requests are being redirected "
                        "to ΔΟΥ Κατοίκων Εξωτερικού to avoid processing legitimate claims regarding AFM 051422558 and AFM 044594747."
                    )
                    
                    # Prepare the TO/CC list from Config for Slack formatting
                    to_list = ", ".join(config.STRIKE_TO)
                    cc_domestic = ", ".join(config.STRIKE_CC_DOMESTIC)
                    cc_intl = ", ".join(config.STRIKE_CC_INTL)
                    
                    msg = f"🚨 DEADLINE MISSED: MinDigital Protocol {protocol_num} remains unresolved after 06/03/2026."
                    attachments = [{
                        "color": "#FF0000",
                        "title": "Data Integrity Violation Alert (Ref: docs/MinDigital/2026-03-06_Data_Integrity_Notice.md)",
                        "text": msg,
                        "fields": [
                            {"title": "System ID", "value": "ZEUS-MD-20260306-001", "short": True},
                            {"title": "Violation Excerpt", "value": excerpt, "short": False},
                            {"title": "Statutory Strike Recipients (TO)", "value": to_list, "short": False},
                            {"title": "Statutory Strike CC (Domestic)", "value": cc_domestic, "short": False},
                            {"title": "Statutory Strike CC (International)", "value": cc_intl, "short": False}
                        ],
                        "footer": "EPPO / SDOE / FBI Escalation Prepared"
                    }]
                    
                    self._save_alert(protocol_num, "deadline_missed", "CRITICAL", msg, details=excerpt)
                    send_alerts(msg, "CRITICAL", attachments)

    def check_protocol(self, protocol_num: str) -> ProtocolStatus:
        """Check a single protocol's status on MyAADE."""
        status = ProtocolStatus(protocol_number=protocol_num)
        try:
            self.driver.get(config.MYAADE_INBOX)
            wait = WebDriverWait(self.driver, 20)
            
            # Wait for search box or result table
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            page_source = self.driver.page_source
            status.raw_html_length = len(page_source)
            status.page_source_hash = hashlib.sha256(page_source.encode()).hexdigest()
            status.status_text = self.driver.find_element(By.TAG_NAME, "body").text[:500]

            defl_type, defl_sev, defl_desc = analyze_deflection(page_source)
            if defl_type:
                status.deflection_type = defl_type
                status.deflection_severity = defl_sev

            prev_hash = self._get_previous_status(protocol_num)
            if prev_hash and prev_hash != status.page_source_hash:
                status.changed = True

            ss_path, ss_hash = capture_screenshot(self.driver, protocol_num, config.SCREENSHOT_DIR)
            status.screenshot_path = ss_path
            status.screenshot_hash = ss_hash

            # Trigger deadline check
            self._check_mindigital_deadline(protocol_num, status)

        except Exception as e:
            logger.error("Error checking protocol %s: %s", protocol_num, e)
            status.status_text = f"ERROR: {str(e)[:200]}"
        return status

    def run_check_cycle(self) -> Dict[str, Any]:
        """Run one complete monitoring cycle."""
        cycle_start = datetime.now(timezone.utc).isoformat()
        results = []
        alerts_count = 0
        errors = 0

        run_cursor = self.db.execute("INSERT INTO monitor_runs (started_at) VALUES (?)", (cycle_start,))
        run_id = run_cursor.lastrowid
        self.db.commit()

        for protocol_num in config.TRACKED_PROTOCOLS:
            if not self.running: break
            status = self.check_protocol(protocol_num)
            self._save_check(status)
            if status.changed or status.deflection_type:
                alerts_count += 1
            if status.status_text.startswith("ERROR:"):
                errors += 1
            results.append(asdict(status))

        self.db.execute(
            "UPDATE monitor_runs SET completed_at = ?, protocols_checked = ?, alerts_generated = ?, errors = ?, status = 'completed' WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), len(results), alerts_count, errors, run_id)
        )
        self.db.commit()
        return {"run_id": run_id, "protocols_checked": len(results), "alerts": alerts_count, "errors": errors}

    def start(self) -> None:
        """Start the continuous monitoring loop."""
        self.db = init_database(config.DB_PATH)
        self.driver = self._create_driver()
        if not self._login_taxisnet():
            self.shutdown()
            return
        
        while self.running:
            try:
                self.run_check_cycle()
                time.sleep(config.CHECK_INTERVAL)
            except Exception as e:
                logger.error("Error in loop: %s", e)
                time.sleep(60)
        self.shutdown()

    def shutdown(self) -> None:
        """Graceful shutdown."""
        if self.driver: self.driver.quit()
        if self.db: self.db.close()

def main():
    monitor = ZeusMonitor()
    monitor.start()

if __name__ == '__main__':
    main()

# ---------------------------------------------------------------------------
# PROTOCOL #175 / SKONICAPROT TRAP DETECTION (Added April 8, 2026)
# ---------------------------------------------------------------------------
# Certificate 504 Institutional Trap: Dimos Spetson issued Certificate 504
# with knowledge of the KED/AADE data mismatch (documented in Protocol #175,
# SKONICAPROT internal communication). YPES AP 14693 blessed the certificate
# without reviewing Protocol #175. The defect blocks D210 filing, inheritance
# access, and proof of standing before every downstream authority.
# The trap is self-sealing: the defective document prevents the complaint
# that would expose the defect. Cite Protocol #175 in all future filings.
# Reference: C-14 in zeus-ai-evidence-package/irs-ci-package/tabs/tab2-contradiction-matrix.md
# ---------------------------------------------------------------------------

SKONICAPROT_TRAP_PROTOCOLS = [
    "175",   # Protocol #175 — SKONICAPROT internal communication
    "504",   # Certificate 504 — defective instrument issued with known mismatch
]

# Δ210 Submission Tracking (from PR #4 / Feb 26, 2026)
D210_PROTOCOL_ID: str = os.getenv("D210_PROTOCOL_ID", "")
D210_DB_PATH: str = os.getenv("D210_DB_PATH", "/app/data/myaade_monitor.db")

# Additional DB table for Δ210 submissions and SKONICAPROT trap tracking
CREATE_D210_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS d210_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_number TEXT NOT NULL,
    submitting_doy TEXT,
    status TEXT DEFAULT 'pending',
    deflection_type TEXT,
    doy_response TEXT,
    cover_letter_excerpt TEXT,
    slack_alerted INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skonicaprot_trap_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    protocol_ref TEXT NOT NULL,
    certificate_ref TEXT,
    agency TEXT,
    detected_at TEXT NOT NULL,
    description TEXT,
    severity TEXT DEFAULT 'CRITICAL',
    linked_afm TEXT,
    slack_alerted INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_d210_protocol
    ON d210_submissions(protocol_number);
CREATE INDEX IF NOT EXISTS idx_skonicaprot_detected
    ON skonicaprot_trap_events(detected_at);
"""


def init_d210_schema(conn: sqlite3.Connection) -> None:
    """Extend the database with Δ210 and SKONICAPROT trap tables."""
    try:
        conn.executescript(CREATE_D210_SCHEMA_SQL)
        conn.commit()
        logger.info("Δ210 / SKONICAPROT schema initialized.")
    except sqlite3.Error as e:
        logger.error("Failed to init D210 schema: %s", e)


def send_d210_slack_alert(
    webhook_url: str,
    protocol_number: str,
    status: str,
    doy_response: str,
    deflection_type: str,
    cover_letter_excerpt: str = "",
) -> bool:
    """Send a rich Slack alert for a Δ210 ENFIA history submission event.

    Embeds the ΔΟΥ response, deflection type, and a cover letter excerpt
    referencing EPPO/SDOE/FBI cross-filing context.
    """
    if not webhook_url or not requests:
        return False
    color = "#FF0000" if deflection_type else "#00AA00"
    excerpt = cover_letter_excerpt or (
        "Formal Δ210 ENFIA history request filed for AFM 051422558 (deceased, "
        "13/06/2021). Any ENFIA billed after death to this AFM, or to KAEK "
        "050681726008 (Keratsini), constitutes unauthorized billing. "
        "Cross-filed: EPPO PP.00179/2026/EN | FBI IC3 | IRS-CI Art.26."
    )
    payload = {
        "attachments": [{
            "color": color,
            "title": f"\u26a0\ufe0f Zeus Δ210 Tracker [{status.upper()}] — Protocol {protocol_number}",
            "fields": [
                {"title": "Protocol #", "value": protocol_number, "short": True},
                {"title": "Status", "value": status, "short": True},
                {"title": "Deflection", "value": deflection_type or "None detected", "short": True},
                {"title": "ΔΟΥ Response Excerpt", "value": doy_response[:300] if doy_response else "(none)", "short": False},
                {"title": "Cover Letter Excerpt", "value": excerpt[:400], "short": False},
            ],
            "footer": "Zeus MyAADE Monitor | Justice for John | EPPO/SDOE/FBI",
            "ts": int(time.time()),
        }]
    }
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as exc:
        logger.error("D210 Slack alert failed: %s", exc)
        return False


def detect_skonicaprot_trap(text: str) -> bool:
    """Detect references to Certificate 504 or SKONICAPROT in a response.

    Protocol #175 (SKONICAPROT) proved the municipality knew the KED/AADE
    mismatch when issuing Certificate 504. Any agency response that cites
    Certificate 504 as valid, or claims no defect, without referencing
    Protocol #175 is exhibiting the institutional trap pattern.
    Returns True if trap indicators are present.
    """
    indicators = [
        "504",                   # Certificate number
        "skonicaprot",           # Internal system reference
        "\u03c0\u03c1\u03c9\u03c4. 175",  # Greek: "πρωτ. 175" (Protocol 175)
        "\u03b2\u03b5\u03b2\u03b1\u03af\u03c9\u03c3\u03b7",  # βεβαίωση (certificate)
        "\u03b4\u03b5\u03bd \u03b4\u03b9\u03b1\u03c0\u03b9\u03c3\u03c4\u03ce\u03bd\u03b5\u03c4\u03b1\u03b9",  # δεν διαπιστώνεται (no defect found)
        "no legal defect",
        "ked/aade",
        "d210",
        "\u03b4210",
    ]
    text_norm = _norm(text)
    return any(_norm(ind) in text_norm for ind in indicators if ind)


def log_skonicaprot_event(
    conn: sqlite3.Connection,
    event_type: str,
    protocol_ref: str,
    certificate_ref: str = "504",
    agency: str = "",
    description: str = "",
    linked_afm: str = "051422558",
    severity: str = "CRITICAL",
) -> int:
    """Log a SKONICAPROT institutional trap detection event.

    Protocol #175 / SKONICAPROT must be cited in all future filings.
    Every detection event is persisted for the audit trail.
    """
    cursor = conn.execute(
        """
        INSERT INTO skonicaprot_trap_events
            (event_type, protocol_ref, certificate_ref, agency,
             detected_at, description, severity, linked_afm)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_type,
            protocol_ref,
            certificate_ref,
            agency,
            datetime.now(timezone.utc).isoformat(),
            description or (
                "Certificate 504 institutional trap detected. "
                "Municipality issued Certificate 504 with knowledge of KED/AADE "
                "mismatch (Protocol #175/SKONICAPROT). YPES AP 14693 blessed it "
                "without reviewing Protocol #175. Trap blocks D210, inheritance, "
                "and standing. Protocol #175 MUST be cited in all future filings."
            ),
            severity,
            linked_afm,
        ),
    )
    conn.commit()
    logger.warning(
        "SKONICAPROT TRAP EVENT logged: %s | Protocol #%s | Cert %s | AFM %s",
        event_type, protocol_ref, certificate_ref, linked_afm,
    )
    return cursor.lastrowid
