from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton, QListWidgetItem
from PySide6.QtCore import Qt, Signal
from pathlib import Path

class HomeWidget(QWidget):
    file_selected = Signal(str)

    def __init__(self, recent_files):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title
        title = QLabel("DarkPDF")
        title.setStyleSheet("font-size: 42px; font-weight: bold; margin-bottom: 5px; color: #2b78e4;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Night-time reading made easy.")
        subtitle.setStyleSheet("font-size: 16px; margin-bottom: 30px; color: #666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Recent Files Label
        recent_label = QLabel("Recent Files")
        recent_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(recent_label, alignment=Qt.AlignmentFlag.AlignLeft)
        
        # Recent Files List
        self.list_widget = QListWidget()
        self.list_widget.setMaximumWidth(600)
        self.list_widget.setMinimumHeight(250)
        self.list_widget.setStyleSheet(
            "QListWidget { font-size: 14px; padding: 5px; border: 1px solid #ccc; border-radius: 5px; }"
            "QListWidget::item { padding: 8px; }"
            "QListWidget::item:hover { background-color: #e0e0e0; }"
        )
        
        if not recent_files:
            item = QListWidgetItem("No recent files found.")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.list_widget.addItem(item)
        else:
            for f in recent_files:
                p = Path(f)
                item = QListWidgetItem(f"{p.name}\n{p.parent}")
                # Optional: use tooltip for full path
                item.setToolTip(str(p.resolve())) 
                self.list_widget.addItem(item)
                
            self.list_widget.itemClicked.connect(self._on_item_clicked)
            
        layout.addWidget(self.list_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Open Button
        btn_open = QPushButton("Open a PDF...")
        btn_open.setMinimumHeight(40)
        btn_open.setMinimumWidth(200)
        btn_open.setStyleSheet(
            "QPushButton { font-size: 16px; font-weight: bold; background-color: #2b78e4; color: white; border-radius: 5px; padding: 10px; }"
            "QPushButton:hover { background-color: #1a5cbb; }"
        )
        btn_open.clicked.connect(lambda: self.file_selected.emit(""))
        
        # Wrap button in layout to center
        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(0, 20, 0, 0)
        btn_layout.addWidget(btn_open, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(btn_layout)
        
        self.recent_files = recent_files

    def _on_item_clicked(self, item):
        idx = self.list_widget.row(item)
        if self.recent_files and 0 <= idx < len(self.recent_files):
            self.file_selected.emit(self.recent_files[idx])
