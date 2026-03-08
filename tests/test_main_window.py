"""Tests for MainWindow — home/PDF switching, shortcuts, zoom slider, notes toggle."""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QStackedWidget
from PySide6.QtCore import Qt

from ui.main_window import MainWindow


class TestMainWindow:
    """GUI tests for MainWindow."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp, temp_pdf, monkeypatch):
        # Isolate settings so tests don't pollute real config
        import tempfile
        from pathlib import Path
        self.tmpdir = tempfile.mkdtemp()
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path(self.tmpdir)))
        
        self.window = MainWindow()
        self.temp_pdf = temp_pdf
        yield
        self.window.close()
        
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ── Home ↔ PDF View Switching ──

    def test_starts_on_home(self):
        """Window should start showing the home view (stacked index 0)."""
        assert self.window.stacked.currentIndex() == 0

    def test_open_file_switches_to_pdf(self):
        """Opening a PDF should switch to PDF view (stacked index 1)."""
        self.window.open_file(self.temp_pdf)
        assert self.window.stacked.currentIndex() == 1

    def test_go_home_switches_back(self):
        """Going home should switch back to index 0."""
        self.window.open_file(self.temp_pdf)
        self.window._go_home()
        assert self.window.stacked.currentIndex() == 0

    def test_home_then_reopen(self):
        """Opening a PDF → Home → Opening again should not crash."""
        self.window.open_file(self.temp_pdf)
        assert self.window.stacked.currentIndex() == 1
        
        self.window._go_home()
        assert self.window.stacked.currentIndex() == 0
        
        # This was the crasher — scroll_area was destroyed by setCentralWidget
        self.window.open_file(self.temp_pdf)
        assert self.window.stacked.currentIndex() == 1
        assert self.window.viewer.renderer.doc is not None

    def test_home_hides_sidebars(self):
        """Going home should hide sidebar and notes docks."""
        self.window.open_file(self.temp_pdf)
        self.window._go_home()
        assert not self.window.sidebar_dock.isVisible()
        assert not self.window.notes_dock.isVisible()

    # ── Zoom Slider ──

    def test_zoom_slider_initial(self):
        """Zoom slider should start at 100."""
        assert self.window.zoom_slider.value() == 100

    def test_zoom_in_updates_slider(self):
        """zoom_in should increase the slider value."""
        self.window.open_file(self.temp_pdf)
        self.window.zoom_in()
        assert self.window.zoom_slider.value() > 100

    def test_zoom_out_updates_slider(self):
        """zoom_out should decrease the slider value."""
        self.window.open_file(self.temp_pdf)
        self.window.zoom_out()
        assert self.window.zoom_slider.value() < 100

    def test_zoom_slider_changes_viewer(self):
        """Dragging zoom slider should change viewer zoom."""
        self.window.open_file(self.temp_pdf)
        self.window.zoom_slider.setValue(200)
        assert abs(self.window.viewer.zoom - 2.0) < 0.01

    # ── Notes Toggle ──

    def test_notes_hidden_on_open(self):
        """Notes dock should be hidden when opening a PDF."""
        self.window.open_file(self.temp_pdf)
        assert not self.window.notes_dock.isVisible()

    def test_toggle_notes(self):
        """Toggling notes button should update checked state and dock visibility flag."""
        assert not self.window.notes_btn.isChecked()
        self.window.notes_btn.click()
        assert self.window.notes_btn.isChecked()
        self.window.notes_btn.click()
        assert not self.window.notes_btn.isChecked()

    # ── Dark Mode ──

    def test_dark_mode_toggle_sync(self):
        """Dark mode toggle should sync menu action and button."""
        self.window._on_dark_mode_toggled(True)
        assert self.window.dark_mode_btn.isChecked()
        assert self.window.dark_mode_action_menu.isChecked()
        
        self.window._on_dark_mode_toggled(False)
        assert not self.window.dark_mode_btn.isChecked()
        assert not self.window.dark_mode_action_menu.isChecked()

    # ── Tool Mode Toggles ──

    def test_highlight_mode_toggle(self):
        """Toggling highlight mode should set interaction mode."""
        from ui.pdf_label import InteractionMode
        self.window._toggle_highlight_mode(True)
        assert self.window.central_label.mode == InteractionMode.HIGHLIGHT
        assert self.window.highlight_btn.isChecked()

    def test_eraser_mode_toggle(self):
        """Toggling eraser mode should set interaction mode."""
        from ui.pdf_label import InteractionMode
        self.window._toggle_eraser_mode(True)
        assert self.window.central_label.mode == InteractionMode.ERASER
        assert self.window.eraser_btn.isChecked()

    def test_modes_are_exclusive(self):
        """Activating highlight should deactivate eraser and vice versa."""
        self.window._toggle_highlight_mode(True)
        assert self.window.highlight_btn.isChecked()
        
        self.window._toggle_eraser_mode(True)
        assert self.window.eraser_btn.isChecked()
        assert not self.window.highlight_btn.isChecked()

    # ── Undo Button ──

    def test_undo_button_exists(self):
        """Undo button should exist in the toolbar."""
        assert hasattr(self.window, 'undo_btn')
        assert self.window.undo_btn is not None

    # ── Page Navigation ──

    def test_page_input_navigation(self):
        """Typing a page number and pressing enter should navigate."""
        self.window.open_file(self.temp_pdf)
        self.window.page_input.setText("2")
        self.window._on_page_input_entered()
        assert self.window.viewer.current_page == 1  # 0-indexed

    def test_page_input_invalid(self):
        """Invalid page input should revert to current page."""
        self.window.open_file(self.temp_pdf)
        self.window.page_input.setText("abc")
        self.window._on_page_input_entered()
        assert self.window.page_input.text() == "1"  # stays on page 1

    def test_page_input_out_of_bounds(self):
        """Out-of-bounds page input should revert."""
        self.window.open_file(self.temp_pdf)
        self.window.page_input.setText("999")
        self.window._on_page_input_entered()
        assert self.window.page_input.text() == "1"
