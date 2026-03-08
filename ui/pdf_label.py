from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, QRect, Signal
from enum import Enum, auto

class InteractionMode(Enum):
    NORMAL = auto()
    HIGHLIGHT = auto()
    COMMENT = auto()
    ERASER = auto()

class PDFViewerLabel(QLabel):
    highlight_requested = Signal(QRect)
    comment_requested = Signal(QRect)
    erase_requested = Signal(QRect)
    link_clicked = Signal(dict)

    def __init__(self):
        super().__init__()
        self.start_pos = None
        self.current_pos = None
        self.mode = InteractionMode.NORMAL
        self.links = []
        self.setMouseTracking(True)

    def set_links(self, links):
        self.links = links
        self.update()

    def mousePressEvent(self, event):
        if self.mode == InteractionMode.NORMAL:
            return
            
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.position().toPoint()
            self.current_pos = self.start_pos
            self.update()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        
        if event.buttons() & Qt.MouseButton.LeftButton and self.start_pos:
            self.current_pos = pos
            self.update()
        elif self.mode == InteractionMode.NORMAL:
            # Check for link hover
            is_hovering_link = any(link["rect"].contains(pos) for link in self.links)
            if is_hovering_link:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if self.mode == InteractionMode.NORMAL:
            if event.button() == Qt.MouseButton.LeftButton and self.start_pos:
                # Detect click without dragging
                self.current_pos = event.position().toPoint()
                dist = (self.current_pos - self.start_pos).manhattanLength()
                if dist < 5:
                    for link in self.links:
                        if link["rect"].contains(self.current_pos):
                            self.link_clicked.emit(link)
                            break
                self.start_pos = None
            return
            
        if event.button() == Qt.MouseButton.LeftButton and self.start_pos:
            self.current_pos = event.position().toPoint()
            rect = QRect(self.start_pos, self.current_pos).normalized()
            # Require at least an 8x8 pixel drag to count as a selection
            if rect.width() > 8 and rect.height() > 8:
                if self.mode == InteractionMode.HIGHLIGHT:
                    self.highlight_requested.emit(rect)
                elif self.mode == InteractionMode.COMMENT:
                    self.comment_requested.emit(rect)
                elif self.mode == InteractionMode.ERASER:
                    self.erase_requested.emit(rect)
                
            self.start_pos = None
            self.current_pos = None
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.start_pos and self.current_pos and self.mode != InteractionMode.NORMAL:
            painter = QPainter(self)
            
            if self.mode == InteractionMode.HIGHLIGHT:
                painter.setPen(QPen(QColor(255, 255, 0, 200), 2))
                painter.setBrush(QColor(255, 255, 0, 50))
            elif self.mode == InteractionMode.COMMENT:
                painter.setPen(QPen(QColor(0, 150, 255, 200), 2))
                painter.setBrush(QColor(0, 150, 255, 50))
            elif self.mode == InteractionMode.ERASER:
                painter.setPen(QPen(QColor(255, 100, 100, 200), 2))
                painter.setBrush(QColor(255, 100, 100, 50))
                
            rect = QRect(self.start_pos, self.current_pos).normalized()
            painter.drawRect(rect)
