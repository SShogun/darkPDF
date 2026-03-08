from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QListView
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon
from utils.image_utils import get_qimage

class MinimapWidget(QListWidget):
    page_selected = pyqtSignal(int)

    def __init__(self, renderer):
        super().__init__()
        self.renderer = renderer
        
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setIconSize(QSize(60, 85))
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setSpacing(5)
        self.setStyleSheet(
            "QListWidget { background-color: transparent; border: none; outline: 0; }"
            "QListWidget::item { background-color: #222; border-radius: 5px; padding: 5px; }"
            "QListWidget::item:selected { background-color: #444; border: 2px solid #2b78e4; }"
        )
        
        self.itemClicked.connect(self._on_item_clicked)

    def load_minimap(self, dark_mode=False, bboxes_func=None, theme=None):
        self.clear()
        if not self.renderer.doc:
            return
            
        page_count = self.renderer.get_page_count()
        # Render a tiny thumbnail of each page
        # Note: This loads all thumbnails synchronously, which is okay for small PDFs.
        # For huge PDFs we'd want a background thread, but this works for MVP.
        zoom = 0.05
        for i in range(page_count):
            pix = self.renderer.get_page_pixmap(i, zoom=zoom)
            
            # Use smart dark mode for minimap if requested
            bboxes = []
            if bboxes_func and dark_mode:
                bboxes = bboxes_func(i, zoom)
                
            if pix:
                qimg = get_qimage(pix, dark_mode, bboxes, theme)
                from PyQt6.QtGui import QPixmap
                qpixmap = QPixmap.fromImage(qimg)
                
                item = QListWidgetItem()
                item.setIcon(QIcon(qpixmap))
                item.setData(Qt.ItemDataRole.UserRole, i)
                self.addItem(item)
                
    def select_page(self, index: int):
        if 0 <= index < self.count():
            self.setCurrentRow(index)

    def _on_item_clicked(self, item):
        page_index = item.data(Qt.ItemDataRole.UserRole)
        self.page_selected.emit(page_index)
