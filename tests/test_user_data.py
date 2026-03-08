"""Tests for UserDataManager — settings persistence, recent files, notes, theme."""
import sys
import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestUserDataManager:
    """Tests for UserDataManager, using an isolated temp config dir."""

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch, temp_pdf):
        """Set up an isolated UserDataManager for each test."""
        self.tmpdir = tempfile.mkdtemp()
        original_home = Path.home
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path(self.tmpdir)))
        
        from utils.user_data_manager import UserDataManager
        self.manager = UserDataManager()
        self.test_pdf = temp_pdf
        
        yield
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ── Recent Files ──

    def test_add_recent_file(self):
        """Adding a file should put it at the top of recent files."""
        self.manager.add_recent_file(self.test_pdf)
        recents = self.manager.get_recent_files()
        assert len(recents) >= 1
        assert Path(recents[0]).resolve() == Path(self.test_pdf).resolve()

    def test_recent_files_dedup(self):
        """Adding the same file twice should not create duplicates."""
        self.manager.add_recent_file(self.test_pdf)
        self.manager.add_recent_file(self.test_pdf)
        recents = self.manager.get_recent_files()
        assert recents.count(str(Path(self.test_pdf).resolve())) == 1

    def test_recent_files_filters_deleted(self):
        """Deleted files should be filtered out of recent files."""
        # Add a file that doesn't exist
        fake_path = os.path.join(self.tmpdir, "nonexistent.pdf")
        self.manager.data["recent_files"].append(fake_path)
        recents = self.manager.get_recent_files()
        assert fake_path not in recents

    # ── Page Progress ──

    def test_page_progress_default(self):
        """Default last read page should be 0."""
        page = self.manager.get_last_read_page(self.test_pdf)
        assert page == 0

    def test_page_progress_save_load(self):
        """Setting and getting page progress should round-trip."""
        self.manager.set_last_read_page(self.test_pdf, 5)
        assert self.manager.get_last_read_page(self.test_pdf) == 5

    # ── Notes ──

    def test_notes_default_empty(self):
        """Default note for any page should be empty string."""
        note = self.manager.get_note(self.test_pdf, 0)
        assert note == ""

    def test_notes_save_load(self):
        """Setting and getting notes should round-trip."""
        self.manager.set_note(self.test_pdf, 2, "Important section here")
        assert self.manager.get_note(self.test_pdf, 2) == "Important section here"

    def test_notes_per_page(self):
        """Notes should be independent per page."""
        self.manager.set_note(self.test_pdf, 0, "Page 0 note")
        self.manager.set_note(self.test_pdf, 1, "Page 1 note")
        assert self.manager.get_note(self.test_pdf, 0) == "Page 0 note"
        assert self.manager.get_note(self.test_pdf, 1) == "Page 1 note"

    # ── Theme ──

    def test_theme_defaults(self):
        """Theme should have sensible defaults."""
        theme = self.manager.get_theme_settings()
        assert "dark_mode" in theme
        assert "brightness" in theme

    def test_theme_set_dark_mode(self):
        """Setting dark mode should persist."""
        self.manager.set_theme_setting("dark_mode", True)
        assert self.manager.get_theme_settings()["dark_mode"] is True

    def test_theme_set_brightness(self):
        """Setting brightness should persist."""
        self.manager.set_theme_setting("brightness", 0.5)
        assert self.manager.get_theme_settings()["brightness"] == 0.5

    # ── Persistence ──

    def test_settings_persist_to_disk(self):
        """Settings should be saved to and loaded from disk."""
        self.manager.set_theme_setting("dark_mode", True)
        self.manager.add_recent_file(self.test_pdf)
        self.manager.set_note(self.test_pdf, 0, "Test note")
        
        # Create a new manager — should load from same file
        from utils.user_data_manager import UserDataManager
        manager2 = UserDataManager()
        
        assert manager2.get_theme_settings()["dark_mode"] is True
        assert len(manager2.get_recent_files()) >= 1
        assert manager2.get_note(self.test_pdf, 0) == "Test note"
