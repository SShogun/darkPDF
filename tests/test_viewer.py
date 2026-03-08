"""Tests for ViewerController and PDFRenderer — zoom, navigation, undo."""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from renderer import PDFRenderer
from viewer import ViewerController


class TestPDFRenderer:
    """Tests for the PDFRenderer class (no GUI needed)."""

    def test_load_valid_pdf(self, temp_pdf):
        """Loading a valid PDF should succeed."""
        r = PDFRenderer()
        assert r.load_document(temp_pdf) is True
        assert r.doc is not None

    def test_load_invalid_path(self):
        """Loading a nonexistent file should fail gracefully."""
        r = PDFRenderer()
        assert r.load_document("/nonexistent/file.pdf") is False
        assert r.doc is None

    def test_page_count(self, temp_pdf):
        """Page count should match the test PDF (3 pages)."""
        r = PDFRenderer()
        r.load_document(temp_pdf)
        assert r.get_page_count() == 3

    def test_page_count_no_doc(self):
        """Page count should be 0 when no document is loaded."""
        r = PDFRenderer()
        assert r.get_page_count() == 0

    def test_get_page_pixmap(self, temp_pdf):
        """Getting a page pixmap should return a valid pixmap."""
        r = PDFRenderer()
        r.load_document(temp_pdf)
        pix = r.get_page_pixmap(0, 1.0)
        assert pix is not None
        assert pix.width > 0
        assert pix.height > 0

    def test_get_page_pixmap_zoomed(self, temp_pdf):
        """Zoomed pixmap should be larger than 1x pixmap."""
        r = PDFRenderer()
        r.load_document(temp_pdf)
        pix_1x = r.get_page_pixmap(0, 1.0)
        pix_2x = r.get_page_pixmap(0, 2.0)
        assert pix_2x.width > pix_1x.width
        assert pix_2x.height > pix_1x.height

    def test_get_page_pixmap_out_of_bounds(self, temp_pdf):
        """Out-of-bounds page index should return None."""
        r = PDFRenderer()
        r.load_document(temp_pdf)
        assert r.get_page_pixmap(-1, 1.0) is None
        assert r.get_page_pixmap(99, 1.0) is None

    def test_close_document(self, temp_pdf):
        """Closing should set doc to None."""
        r = PDFRenderer()
        r.load_document(temp_pdf)
        r.close_document()
        assert r.doc is None
        assert r.get_page_count() == 0


class TestViewerController:
    """Tests for ViewerController — navigation, zoom, undo."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp, temp_pdf):
        self.viewer = ViewerController()
        self.temp_pdf = temp_pdf
        self.rendered_pages = []
        self.viewer.page_rendered.connect(lambda img: self.rendered_pages.append(img))

    # ── Document Loading ──

    def test_open_document(self):
        """Opening a document should emit document_loaded and render page 0."""
        self.viewer.open_document(self.temp_pdf)
        assert self.viewer.renderer.doc is not None
        assert self.viewer.current_page == 0
        assert len(self.rendered_pages) >= 1

    def test_open_clears_undo(self):
        """Opening a new document should clear the undo stack."""
        self.viewer.open_document(self.temp_pdf)
        self.viewer._undo_stack.append(("dummy",))
        self.viewer.open_document(self.temp_pdf)
        assert len(self.viewer._undo_stack) == 0

    # ── Page Navigation ──

    def test_next_page(self):
        """next_page should advance by 1."""
        self.viewer.open_document(self.temp_pdf)
        self.viewer.next_page()
        assert self.viewer.current_page == 1

    def test_next_page_at_end(self):
        """next_page at last page should not go beyond."""
        self.viewer.open_document(self.temp_pdf)
        self.viewer.current_page = 2  # last page (0-indexed, 3 pages)
        self.viewer.next_page()
        assert self.viewer.current_page == 2

    def test_prev_page(self):
        """prev_page should go back by 1."""
        self.viewer.open_document(self.temp_pdf)
        self.viewer.current_page = 2
        self.viewer.prev_page()
        assert self.viewer.current_page == 1

    def test_prev_page_at_start(self):
        """prev_page at page 0 should stay at 0."""
        self.viewer.open_document(self.temp_pdf)
        self.viewer.prev_page()
        assert self.viewer.current_page == 0

    # ── Zoom ──

    def test_set_zoom(self):
        """set_zoom should update zoom level."""
        self.viewer.open_document(self.temp_pdf)
        self.viewer.set_zoom(2.0)
        assert self.viewer.zoom == 2.0

    def test_zoom_clamp_min(self):
        """Zoom should not go below 0.25."""
        self.viewer.set_zoom(0.01)
        assert self.viewer.zoom == 0.25

    def test_zoom_clamp_max(self):
        """Zoom should not go above 5.0."""
        self.viewer.set_zoom(10.0)
        assert self.viewer.zoom == 5.0

    # ── Undo ──

    def test_undo_empty_stack(self):
        """Undo with empty stack should return False."""
        self.viewer.open_document(self.temp_pdf)
        assert self.viewer.undo() is False

    def test_undo_after_highlight(self):
        """Adding a highlight then undoing should restore annotation count to 0."""
        self.viewer.open_document(self.temp_pdf)
        
        # Page should start with 0 annotations
        from PySide6.QtCore import QRect
        page = self.viewer.renderer.doc.load_page(0)
        initial_count = len(list(page.annots()))
        assert initial_count == 0
        
        # Add a highlight
        self.viewer.add_highlight(QRect(50, 50, 200, 30))
        page = self.viewer.renderer.doc.load_page(0)
        assert len(list(page.annots())) > 0
        
        # Undo
        result = self.viewer.undo()
        assert result is True
        page = self.viewer.renderer.doc.load_page(0)
        assert len(list(page.annots())) == 0

    def test_undo_after_erase(self):
        """Erasing a highlight then undoing should restore the highlight."""
        self.viewer.open_document(self.temp_pdf)
        from PySide6.QtCore import QRect
        
        # First add a highlight (creates an undo entry)
        self.viewer.add_highlight(QRect(50, 50, 200, 30))
        page = self.viewer.renderer.doc.load_page(0)
        count_after_add = len(list(page.annots()))
        assert count_after_add > 0
        
        # Erase it (creates another undo entry)
        self.viewer.erase_highlight(QRect(0, 0, 1000, 1000))
        page = self.viewer.renderer.doc.load_page(0)
        assert len(list(page.annots())) == 0
        
        # Undo erase — highlight should be restored
        self.viewer.undo()
        page = self.viewer.renderer.doc.load_page(0)
        assert len(list(page.annots())) > 0

    def test_undo_stack_limit(self):
        """Undo stack should not exceed MAX_UNDO_STEPS."""
        self.viewer.open_document(self.temp_pdf)
        from PySide6.QtCore import QRect
        
        for i in range(25):
            self.viewer.add_highlight(QRect(50, 50 + i, 200, 30))
        
        assert len(self.viewer._undo_stack) <= ViewerController.MAX_UNDO_STEPS

    # ── Links ──

    def test_links_extracted(self):
        """Viewer should extract links from the page if any exist."""
        # For simplicity, we just test that the signal fires with a list
        links_emitted = []
        self.viewer.links_extracted.connect(lambda links: links_emitted.append(links))
        self.viewer.open_document(self.temp_pdf)
        assert len(links_emitted) > 0
        assert isinstance(links_emitted[0], list)

    # ── Dark Mode ──

    def test_toggle_dark_mode(self):
        """Toggling dark mode should update the flag."""
        self.viewer.open_document(self.temp_pdf)
        self.viewer.toggle_dark_mode(True)
        assert self.viewer.dark_mode is True
        self.viewer.toggle_dark_mode(False)
        assert self.viewer.dark_mode is False
