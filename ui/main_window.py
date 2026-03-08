from PySide6.QtWidgets import QMainWindow, QFileDialog, QLabel, QScrollArea, QToolBar
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtCore import Qt

from viewer import ViewerController

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DarkPDF")
        self.resize(800, 600)

        # Create viewer controller
        self.viewer = ViewerController()
        self.viewer.page_rendered.connect(self.display_page)
        self.viewer.document_loaded.connect(self.document_loaded)

        # Create central layout with scroll area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.central_label = QLabel("Open a PDF to begin reading")
        self.central_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.central_label)
        
        self.setCentralWidget(self.scroll_area)

        self._create_menu()
        self._create_toolbar()

    def _create_menu(self):
        menu_bar = self.menuBar()
        
        # File Menu
        file_menu = menu_bar.addMenu("File")

        open_action = QAction("Open PDF", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        # View Menu
        view_menu = menu_bar.addMenu("View")
        
        # Dark Mode Toggle
        dark_mode_action = QAction("Dark Mode", self)
        dark_mode_action.setCheckable(True)
        dark_mode_action.triggered.connect(self.viewer.toggle_dark_mode)
        view_menu.addAction(dark_mode_action)
        
        view_menu.addSeparator()
        
        prev_action = QAction("Previous Page", self)
        prev_action.setShortcut("Left")
        prev_action.triggered.connect(self.viewer.prev_page)
        view_menu.addAction(prev_action)
        
        next_action = QAction("Next Page", self)
        next_action.setShortcut("Right")
        next_action.triggered.connect(self.viewer.next_page)
        view_menu.addAction(next_action)
        
        view_menu.addSeparator()
        
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut("Ctrl+=")
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)

    def _create_toolbar(self):
        toolbar = QToolBar("Navigation", self)
        self.addToolBar(toolbar)
        
        dark_mode_action = QAction("Dark Mode", self)
        dark_mode_action.setCheckable(True)
        dark_mode_action.triggered.connect(self.viewer.toggle_dark_mode)
        toolbar.addAction(dark_mode_action)
        
        toolbar.addSeparator()
        
        prev_action = QAction("Prev", self)
        prev_action.triggered.connect(self.viewer.prev_page)
        toolbar.addAction(prev_action)
        
        next_action = QAction("Next", self)
        next_action.triggered.connect(self.viewer.next_page)
        toolbar.addAction(next_action)
        
        toolbar.addSeparator()
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)
        
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

    def zoom_in(self):
        self.viewer.set_zoom(self.viewer.zoom * 1.2)

    def zoom_out(self):
        self.viewer.set_zoom(self.viewer.zoom / 1.2)

    def open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
             self,
             "Open PDF",
             "",
             "PDF Files (*.pdf)"
        )
        if filepath:
            print(f"Opening file: {filepath}")
            self.viewer.open_document(filepath)
            
    def document_loaded(self, page_count: int):
        self.setWindowTitle(f"DarkPDF - {page_count} pages")

    def display_page(self, qimage):
        qpixmap = QPixmap.fromImage(qimage)
        self.central_label.setPixmap(qpixmap)
        self.central_label.resize(qpixmap.size())
