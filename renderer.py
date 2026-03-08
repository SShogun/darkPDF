import fitz

class PDFRenderer:
    def __init__(self):
        self.doc = None

    def load_document(self, filepath: str) -> bool:
        try:
            self.doc = fitz.open(filepath)
            return True
        except Exception as e:
            print(f"Failed to load PDF: {e}")
            return False

    def close_document(self):
        if self.doc:
            self.doc.close()
            self.doc = None
            
    def get_page_count(self) -> int:
        if self.doc:
            return self.doc.page_count
        return 0

    def get_page_pixmap(self, page_index: int, zoom: float = 1.0) -> fitz.Pixmap:
        if not self.doc or page_index < 0 or page_index >= self.get_page_count():
            return None
        page = self.doc.load_page(page_index)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        return pix
