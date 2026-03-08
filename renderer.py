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

    def get_page_image_bboxes(self, page_index: int, zoom: float = 1.0) -> list:
        if not self.doc or page_index < 0 or page_index >= self.get_page_count():
            return []
        page = self.doc.load_page(page_index)
        bboxes = []
        # get_image_info returns list of dicts with 'bbox' keys
        for img in page.get_image_info():
            rect = img.get("bbox")
            if rect:
                # scale PyMuPDF default 72dpi rect by our zoom matrix
                scaled_rect = fitz.Rect(
                    rect[0] * zoom,
                    rect[1] * zoom,
                    rect[2] * zoom,
                    rect[3] * zoom
                )
                bboxes.append(scaled_rect)
        return bboxes
