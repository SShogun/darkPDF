"""Shared test fixtures for DarkPDF test suite."""
import sys
import os
import pytest
import tempfile
import shutil

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz
from PyQt6.QtWidgets import QApplication


# ── QApplication singleton (required for all Qt widget tests) ──

@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ── Temporary PDF file ──

@pytest.fixture
def temp_pdf():
    """Create a minimal 3-page PDF in a temp directory for testing."""
    tmpdir = tempfile.mkdtemp()
    pdf_path = os.path.join(tmpdir, "test.pdf")
    
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=612, height=792)  # US Letter
        page.insert_text((72, 72), f"Test Page {i + 1}", fontsize=24)
        
        # Add a dummy URI link to page 0
        if i == 0:
            rect = fitz.Rect(72, 72, 200, 100)
            page.insert_link({"kind": fitz.LINK_URI, "from": rect, "uri": "https://example.com"})
            
    doc.save(pdf_path)
    doc.close()
    
    yield pdf_path
    
    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)


# ── Temporary config directory (isolates UserDataManager from real settings) ──

@pytest.fixture
def temp_config_dir(monkeypatch):
    """Redirect UserDataManager to a temp config directory."""
    tmpdir = tempfile.mkdtemp()
    
    # Monkeypatch Path.home() to redirect config
    from pathlib import Path
    original_home = Path.home
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path(tmpdir)))
    
    yield tmpdir
    
    shutil.rmtree(tmpdir, ignore_errors=True)
