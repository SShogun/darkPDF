from PySide6.QtCore import QObject, Signal, QRect
from PySide6.QtGui import QImage
import fitz

from renderer import PDFRenderer
from utils.image_utils import get_qimage

class ViewerController(QObject):
    # Sends out QImage objects when a page is rendered
    page_rendered = Signal(QImage)
    document_loaded = Signal(int)

    def __init__(self):
        super().__init__()
        self.renderer = PDFRenderer()
        self.current_page = 0
        self.zoom = 1.0
        self.dark_mode = False
        self.theme_settings = {}

    def toggle_dark_mode(self, enabled: bool):
        self.dark_mode = enabled
        self.render_current_page()
        
    def set_theme_settings(self, theme: dict):
        self.theme_settings = theme
        self.render_current_page()

    def open_document(self, filepath: str):
        if self.renderer.load_document(filepath):
            self.current_page = 0
            self.document_loaded.emit(self.renderer.get_page_count())
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

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_current_page()

    def set_zoom(self, zoom: float):
        if 0.1 <= zoom <= 10.0:
            self.zoom = zoom
            self.render_current_page()

    def add_highlight(self, rect: QRect):
        if self.renderer.doc:
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
            
            # Save Document safely (catch Coder=4 error on repaired docs)
            try:
                if not self.renderer.doc.is_repaired:
                    self.renderer.doc.saveIncr()
            except Exception as e:
                print(f"Warning: Could not automatically save highlight: {e}")
            
            # Rerender to show highlights immediately
            self.render_current_page()

    def erase_highlight(self, rect: QRect):
        if self.renderer.doc:
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
                    
            try:
                if not self.renderer.doc.is_repaired:
                    self.renderer.doc.saveIncr()
            except Exception as e:
                print(f"Warning: Could not automatically save highlight deletion: {e}")
                
            self.render_current_page()
