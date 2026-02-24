"""Tests for myaade_monitor_zeus.py — core monitoring engine.

Covers: Config, Database, Deflection Analysis, Notifications,
        ProtocolStatus, Screenshot capture, ZeusMonitor methods.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# We import individual functions/classes to test them in isolation.
from myaade_monitor_zeus import (
    Config,
    DEFLECTION_PATTERNS,
    ProtocolStatus,
    analyze_deflection,
    capture_screenshot,
    init_database,
    send_slack_alert,
    send_discord_alert,
    send_alerts,
    ZeusMonitor,
)


# ===================================================================
# Config Tests
# ===================================================================

class TestConfig:
    """Test the Config class and env-var loading."""

    def test_default_check_interval(self):
        cfg = Config()
        assert isinstance(cfg.CHECK_INTERVAL, int)

    def test_default_headless_true(self):
        cfg = Config()
        assert cfg.HEADLESS is True

    def test_tracked_protocols_default(self):
        cfg = Config()
        assert "214142" in cfg.TRACKED_PROTOCOLS

    def test_afm_constants(self):
        cfg = Config()
        assert cfg.AFM_STAMATINA == "044594747"
        assert cfg.AFM_JOHN_DECEASED == "051422558"

    def test_myaade_urls(self):
        cfg = Config()
        assert "aade.gr" in cfg.MYAADE_BASE
        assert "gsis.gr" in cfg.MYAADE_LOGIN

    def test_db_path_is_path_object(self):
        cfg = Config()
        assert isinstance(cfg.DB_PATH, Path)

    def test_max_retries_default(self):
        cfg = Config()
        assert cfg.MAX_RETRIES >= 1


# ===================================================================
# Database Tests
# ===================================================================

class TestDatabase:
    """Test SQLite database initialization and schema."""

    def test_init_creates_file(self, tmp_path):
        db_path = tmp_path / "test.db"
        conn = init_database(db_path)
        assert db_path.exists()
        conn.close()

    def test_init_creates_tables(self, tmp_path):
        db_path = tmp_path / "test.db"
        conn = init_database(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert "protocol_checks" in tables
        assert "alerts" in tables
        assert "monitor_runs" in tables
        conn.close()

    def test_wal_mode_enabled(self, tmp_path):
        db_path = tmp_path / "test.db"
        conn = init_database(db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_insert_protocol_check(self, tmp_db):
        tmp_db.execute(
            "INSERT INTO protocol_checks "
            "(protocol_number, status_text, checked_at) VALUES (?, ?, ?)",
            ("214142", "Εκκρεμεί", datetime.now(timezone.utc).isoformat()),
        )
        tmp_db.commit()
        row = tmp_db.execute(
            "SELECT protocol_number FROM protocol_checks"
        ).fetchone()
        assert row[0] == "214142"

    def test_insert_alert(self, tmp_db):
        tmp_db.execute(
            "INSERT INTO alerts "
            "(protocol_number, alert_type, severity, message, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("214142", "deflection", "HIGH", "test alert",
             datetime.now(timezone.utc).isoformat()),
        )
        tmp_db.commit()
        count = tmp_db.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        assert count == 1

    def test_idempotent_init(self, tmp_path):
        db_path = tmp_path / "test.db"
        conn1 = init_database(db_path)
        conn1.close()
        conn2 = init_database(db_path)
        tables = conn2.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        assert tables >= 3
        conn2.close()


# ===================================================================
# Deflection Analysis Tests
# ===================================================================

class TestDeflectionAnalysis:
    """Test the analyze_deflection() function."""

    def test_no_deflection_on_clean_text(self):
        dtype, sev, desc = analyze_deflection("Normal status update")
        assert dtype is None
        assert sev is None

    def test_detects_forwarded_greek(self):
        dtype, sev, desc = analyze_deflection("Το αίτημα διαβιβάστηκε στην αρμόδια υπηρεσία")
        assert dtype == "forwarded"
        assert sev == "HIGH"

    def test_detects_forwarded_english(self):
        dtype, sev, desc = analyze_deflection("This has been forwarded to the competent authority")
        assert dtype == "forwarded"

    def test_detects_no_jurisdiction_greek(self):
        dtype, sev, desc = analyze_deflection("Το αίτημα κρίνεται αναρμόδιο")
        assert dtype == "no_jurisdiction"
        assert sev == "CRITICAL"

    def test_detects_responded_greek(self):
        dtype, sev, desc = analyze_deflection("Το πρωτόκολλο απαντήθηκε")
        assert dtype == "responded"
        assert sev == "CRITICAL"

    def test_detects_archived_greek(self):
        dtype, sev, desc = analyze_deflection("Το αίτημα αρχειοθετήθηκε")
        assert dtype == "archived"
        assert sev == "CRITICAL"

    def test_detects_under_review_greek(self):
        dtype, sev, desc = analyze_deflection("Το αίτημα εξετάζεται")
        assert dtype == "under_review"
        assert sev == "WATCH"

    def test_case_insensitive(self):
        dtype, _, _ = analyze_deflection("ΔΙΑΒΙΒΑΣΤΗΚΕ στην υπηρεσία")
        assert dtype == "forwarded"

    def test_empty_string(self):
        dtype, sev, desc = analyze_deflection("")
        assert dtype is None

    def test_deflection_patterns_dict_valid(self):
        for name, pattern in DEFLECTION_PATTERNS.items():
            assert "keywords_el" in pattern
            assert "keywords_en" in pattern
            assert "severity" in pattern
            assert pattern["severity"] in ("CRITICAL", "HIGH", "WATCH", "INFO")


# ===================================================================
# ProtocolStatus Dataclass Tests
# ===================================================================

class TestProtocolStatus:
    """Test the ProtocolStatus dataclass."""

    def test_defaults(self):
        ps = ProtocolStatus(protocol_number="214142")
        assert ps.protocol_number == "214142"
        assert ps.status_text == ""
        assert ps.changed is False
        assert ps.deflection_type is None

    def test_checked_at_auto_populated(self):
        ps = ProtocolStatus(protocol_number="214142")
        assert ps.checked_at  # non-empty
        assert "T" in ps.checked_at  # ISO format


# ===================================================================
# Screenshot Capture Tests
# ===================================================================

class TestScreenshotCapture:
    """Test the capture_screenshot() function."""

    def test_returns_path_and_hash(self, mock_driver, tmp_screenshot_dir):
        # Make save_screenshot actually create a file
        def _save(path):
            Path(path).write_bytes(b"fake png data")
            return True
        mock_driver.save_screenshot.side_effect = _save

        path, file_hash = capture_screenshot(
            mock_driver, "214142", tmp_screenshot_dir
        )
        assert path is not None
        assert file_hash is not None
        assert "214142" in path

    def test_hash_is_sha256(self, mock_driver, tmp_screenshot_dir):
        def _save(path):
            Path(path).write_bytes(b"test data")
            return True
        mock_driver.save_screenshot.side_effect = _save

        _, file_hash = capture_screenshot(
            mock_driver, "214142", tmp_screenshot_dir
        )
        expected = hashlib.sha256(b"test data").hexdigest()
        assert file_hash == expected

    def test_returns_none_on_failure(self, mock_driver, tmp_screenshot_dir):
        mock_driver.save_screenshot.side_effect = Exception("browser crash")
        path, file_hash = capture_screenshot(
            mock_driver, "214142", tmp_screenshot_dir
        )
        assert path is None
        assert file_hash is None

    def test_creates_directory_if_missing(self, mock_driver, tmp_path):
        new_dir = tmp_path / "new_screenshots"
        def _save(path):
            Path(path).write_bytes(b"data")
            return True
        mock_driver.save_screenshot.side_effect = _save

        path, _ = capture_screenshot(mock_driver, "214142", new_dir)
        assert new_dir.exists()


# ===================================================================
# Notification Tests
# ===================================================================

class TestNotifications:
    """Test Slack, Discord, and generic webhook alerts."""

    def test_slack_alert_success(self):
        with patch("myaade_monitor_zeus.requests") as mock_req:
            mock_req.post.return_value = MagicMock(status_code=200)
            result = send_slack_alert("https://hooks.slack.com/test", "Test msg", "INFO")
            assert result is True
            mock_req.post.assert_called_once()

    def test_slack_alert_no_url(self):
        result = send_slack_alert("", "Test msg", "INFO")
        assert result is False

    def test_discord_alert_success(self):
        with patch("myaade_monitor_zeus.requests") as mock_req:
            mock_req.post.return_value = MagicMock(status_code=204)
            result = send_discord_alert("https://discord.com/api/webhooks/test", "Test msg", "HIGH")
            assert result is True

    def test_discord_alert_no_url(self):
        result = send_discord_alert("", "Test msg")
        assert result is False

    def test_slack_handles_network_error(self):
        with patch("myaade_monitor_zeus.requests") as mock_req:
            mock_req.post.side_effect = ConnectionError("Network down")
            result = send_slack_alert("https://hooks.slack.com/test", "msg")
            assert result is False

    def test_discord_handles_network_error(self):
        with patch("myaade_monitor_zeus.requests") as mock_req:
            mock_req.post.side_effect = ConnectionError("Network down")
            result = send_discord_alert("https://discord.com/api/webhooks/test", "msg")
            assert result is False


# ===================================================================
# ZeusMonitor Class Tests
# ===================================================================

class TestZeusMonitor:
    """Test the ZeusMonitor class methods."""

    def test_init_creates_instance(self):
        with patch("myaade_monitor_zeus.signal"):
            monitor = ZeusMonitor()
            assert monitor.running is True
            assert monitor.driver is None
            assert monitor.db is None

    def test_save_check(self, tmp_db):
        with patch("myaade_monitor_zeus.signal"):
            monitor = ZeusMonitor()
            monitor.db = tmp_db
            status = ProtocolStatus(
                protocol_number="214142",
                status_text="Εκκρεμεί",
                page_source_hash="abc123",
            )
            row_id = monitor._save_check(status)
            assert row_id >= 1

            row = tmp_db.execute(
                "SELECT protocol_number, status_text FROM protocol_checks WHERE id = ?",
                (row_id,),
            ).fetchone()
            assert row[0] == "214142"

    def test_save_alert(self, tmp_db):
        with patch("myaade_monitor_zeus.signal"):
            monitor = ZeusMonitor()
            monitor.db = tmp_db
            row_id = monitor._save_alert(
                "214142", "status_change", "CRITICAL", "Status changed!"
            )
            assert row_id >= 1

    def test_get_previous_status_none(self, tmp_db):
        with patch("myaade_monitor_zeus.signal"):
            monitor = ZeusMonitor()
            monitor.db = tmp_db
            result = monitor._get_previous_status("214142")
            assert result is None

    def test_get_previous_status_returns_hash(self, tmp_db):
        with patch("myaade_monitor_zeus.signal"):
            monitor = ZeusMonitor()
            monitor.db = tmp_db
            tmp_db.execute(
                "INSERT INTO protocol_checks "
                "(protocol_number, page_source_hash, checked_at) VALUES (?, ?, ?)",
                ("214142", "hash_abc", datetime.now(timezone.utc).isoformat()),
            )
            tmp_db.commit()
            result = monitor._get_previous_status("214142")
            assert result == "hash_abc"

    def test_shutdown_closes_resources(self):
        with patch("myaade_monitor_zeus.signal"), \
             patch("myaade_monitor_zeus.send_alerts"):
            monitor = ZeusMonitor()
            monitor.driver = MagicMock()
            monitor.db = MagicMock()
            monitor.shutdown()
            monitor.driver.quit.assert_called_once()
            monitor.db.close.assert_called_once()
