from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage
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

    def toggle_dark_mode(self, enabled: bool):
        self.dark_mode = enabled
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
                qimage = get_qimage(pix, self.dark_mode)
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
