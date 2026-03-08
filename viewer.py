from PySide6.QtCore import QObject, Signal, QRect
from PySide6.QtGui import QImage
import fitz
import os
import tempfile
import shutil
import copy

from renderer import PDFRenderer
from utils.image_utils import get_qimage

class ViewerController(QObject):
    # Sends out QImage objects when a page is rendered
    page_rendered = Signal(QImage)
    document_loaded = Signal(int)

    MAX_UNDO_STEPS = 20

    def __init__(self):
        super().__init__()
        self.renderer = PDFRenderer()
        self.current_page = 0
        self.zoom = 1.0
        self.dark_mode = False
        self.theme_settings = {}
        self._undo_stack = []  # list of (page_index, annot_xrefs_snapshot) tuples

    def toggle_dark_mode(self, enabled: bool):
        self.dark_mode = enabled
        self.render_current_page()
        
    def set_theme_settings(self, theme: dict):
        self.theme_settings = theme
        self.render_current_page()

    def open_document(self, filepath: str, initial_page: int = 0):
        if self.renderer.load_document(filepath):
            self._undo_stack.clear()
            self.document_loaded.emit(self.renderer.get_page_count())
            
            if 0 <= initial_page < self.renderer.get_page_count():
                self.current_page = initial_page
            else:
                self.current_page = 0
            
            self.render_current_page()

    def render_current_page(self):
        if self.renderer.doc:
            pix = self.renderer.get_page_pixmap(self.current_page, self.zoom)
            if pix:
                bboxes = self.renderer.get_page_image_bboxes(self.current_page, self.zoom)
                qimage = get_qimage(pix, self.dark_mode, bboxes, self.theme_settings)
                self.page_rendered.emit(qimage)

    def next_page(self):
        if self.current_page < self.renderer.get_page_count() - 1:
            self.current_page += 1
            self.render_current_page()

    def set_zoom(self, new_zoom: float):
        self.zoom = max(0.25, min(new_zoom, 5.0))  # clamp between 25% and 500%
        self.render_current_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_current_page()

    # ── Undo System ──────────────────────────────────────────────

    def _snapshot_page_annots(self, page_index: int) -> bytes:
        """Capture the raw PDF page content so we can restore it on undo.
        We save the full document bytes — simple and reliable for undo."""
        if not self.renderer.doc:
            return None
        page = self.renderer.doc.load_page(page_index)
        # Collect all annotation xrefs and their raw data
        annots_data = []
        for annot in page.annots():
            annots_data.append({
                'xref': annot.xref,
                'rect': tuple(annot.rect),
                'type': annot.type,
                'colors': annot.colors,
                'opacity': annot.opacity,
                'vertices': annot.vertices if annot.vertices else None,
            })
        return annots_data

    def _push_undo(self, page_index: int):
        """Push current page annotation state onto the undo stack."""
        snapshot = self._snapshot_page_annots(page_index)
        self._undo_stack.append((page_index, snapshot))
        # Limit stack size
        if len(self._undo_stack) > self.MAX_UNDO_STEPS:
            self._undo_stack.pop(0)

    def undo(self) -> bool:
        """Undo the last annotation operation. Returns True if undo was performed."""
        if not self._undo_stack or not self.renderer.doc:
            return False

        page_index, old_annots = self._undo_stack.pop()
        page = self.renderer.doc.load_page(page_index)

        # Remove all current annotations on the page
        current_annots = list(page.annots())
        for annot in current_annots:
            page.delete_annot(annot)

        # Restore old annotations
        if old_annots:
            for adata in old_annots:
                rect = fitz.Rect(adata['rect'])
                annot_type = adata['type']
                
                # We only deal with highlight annotations in this app
                if annot_type[0] == fitz.PDF_ANNOT_HIGHLIGHT:
                    if adata.get('vertices'):
                        # Rebuild quads from vertices
                        verts = adata['vertices']
                        quads = []
                        for i in range(0, len(verts), 4):
                            if i + 3 < len(verts):
                                quad = fitz.Quad(verts[i], verts[i+1], verts[i+2], verts[i+3])
                                quads.append(quad)
                        if quads:
                            annot = page.add_highlight_annot(quads)
                        else:
                            annot = page.add_highlight_annot(rect)
                    else:
                        annot = page.add_highlight_annot(rect)
                    
                    # Restore visual properties
                    colors = adata.get('colors', {})
                    stroke = colors.get('stroke')
                    if stroke:
                        annot.set_colors(stroke=stroke)
                    opacity = adata.get('opacity', 0.4)
                    annot.set_opacity(opacity)
                    annot.update()

        self._safe_save_document()
        
        # Navigate to the affected page and re-render
        self.current_page = page_index
        self.render_current_page()
        return True

    # ── Document Save ────────────────────────────────────────────

    def _safe_save_document(self):
        """Attempts incremental save, falls back to full save + reopen if corrupted or repaired."""
        if not self.renderer.doc:
            return
            
        filepath = self.renderer.doc.name
        try:
            if not self.renderer.doc.is_repaired:
                self.renderer.doc.saveIncr()
                return
        except Exception:
            pass # Fallback to full save
            
        # Full save fallback
        # 1. Save to a temporary file
        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
        try:
            self.renderer.doc.save(temp_path)
            
            # 2. To overwrite the original file we must close it first
            self.renderer.doc.close()
            
            # 3. Replace original with temp
            shutil.move(temp_path, filepath)
            
            # 4. Reopen document transparently
            self.renderer.load_document(filepath)
        except Exception as e:
            print(f"Critical error saving PDF: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # ── Annotation Operations ────────────────────────────────────

    def add_highlight(self, rect: QRect):
        if self.renderer.doc:
            # Save undo state BEFORE making changes
            self._push_undo(self.current_page)
            
            # Revert UI scale mapping to original Document scale
            pdf_rect = fitz.Rect(
                rect.left() / self.zoom,
                rect.top() / self.zoom,
                rect.right() / self.zoom,
                rect.bottom() / self.zoom
            )
            page = self.renderer.doc.load_page(self.current_page)
            
            # Fetch words inside the box to highlight precisely
            words = page.get_text("words", clip=pdf_rect)
            if words:
                quads = [fitz.Rect(w[:4]).quad for w in words]
                annot = page.add_highlight_annot(quads)
            else:
                annot = page.add_highlight_annot(pdf_rect)
                
            # Set native color to light blue. In Dark Mode (inversion), this turns into a pleasant orange/yellow!
            annot.set_colors(stroke=(0, 0.5, 1))
            annot.set_opacity(0.4)
            annot.update()
            
            self._safe_save_document()
            self.render_current_page()

    def erase_highlight(self, rect: QRect):
        if self.renderer.doc:
            # Save undo state BEFORE making changes
            self._push_undo(self.current_page)
            
            pdf_rect = fitz.Rect(
                rect.left() / self.zoom,
                rect.top() / self.zoom,
                rect.right() / self.zoom,
                rect.bottom() / self.zoom
            )
            page = self.renderer.doc.load_page(self.current_page)
            
            # Delete any annotations intersecting the eraser box
            for annot in page.annots():
                if annot.rect.intersects(pdf_rect):
                    page.delete_annot(annot)
                    
            self._safe_save_document()
            self.render_current_page()
