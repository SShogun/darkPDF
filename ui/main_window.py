from PySide6.QtWidgets import QMainWindow, QFileDialog, QLabel, QScrollArea, QToolBar, QSlider, QDockWidget, QTextEdit, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLineEdit
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtCore import Qt, QEvent, QRect

from viewer import ViewerController
from ui.home_widget import HomeWidget
from ui.pdf_label import PDFViewerLabel
from ui.minimap import MinimapWidget
from utils.user_data_manager import UserDataManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DarkPDF")
        self.resize(800, 600)
        self.user_data = UserDataManager()

        # Create viewer controller
        self.viewer = ViewerController()
        self.viewer.page_rendered.connect(self.display_page)
        self.viewer.document_loaded.connect(self.document_loaded)

        # Create central layout with scroll area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.central_label = PDFViewerLabel()
        self.central_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.central_label.highlight_requested.connect(self._on_highlight_requested)
        self.central_label.comment_requested.connect(self._on_comment_requested)
        self.central_label.erase_requested.connect(self._on_erase_requested)
        self.scroll_area.setWidget(self.central_label)
        
        # Install event filter for zooming
        self.scroll_area.installEventFilter(self)
        self.scroll_area.viewport().installEventFilter(self)
        
        # Create Notes Dock Widget
        self.notes_dock = QDockWidget("Page Notes", self)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Write notes for this page here...")
        self.notes_edit.setStyleSheet("font-size: 14px; padding: 5px;")
        self.notes_edit.textChanged.connect(self._on_notes_changed)
        self.notes_dock.setWidget(self.notes_edit)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.notes_dock)
        self.notes_dock.hide()

        # Create Navigation Sidebar Dock Widget
        self.sidebar_dock = QDockWidget("Navigation", self)
        self.sidebar_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.sidebar_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures) # make it fixed
        
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        # Interactive Page Navigator
        nav_info_layout = QHBoxLayout()
        self.page_input = QLineEdit()
        self.page_input.setFixedWidth(40)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.page_input.returnPressed.connect(self._on_page_input_entered)
        
        self.total_pages_label = QLabel(" / -")
        self.total_pages_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        nav_info_layout.addWidget(QLabel("Page: "))
        nav_info_layout.addWidget(self.page_input)
        nav_info_layout.addWidget(self.total_pages_label)
        sidebar_layout.addLayout(nav_info_layout)
        
        nav_prev_btn = QPushButton("▲ Prev", self)
        nav_prev_btn.clicked.connect(self.viewer.prev_page)
        
        nav_next_btn = QPushButton("▼ Next", self)
        nav_next_btn.clicked.connect(self.viewer.next_page)
        
        sidebar_layout.addWidget(nav_prev_btn)
        sidebar_layout.addWidget(nav_next_btn)
        
        # Minimap container
        sidebar_layout.addSpacing(10)
        self.minimap_widget = MinimapWidget(self.viewer.renderer)
        self.minimap_widget.page_selected.connect(self._on_minimap_page_selected)
        sidebar_layout.addWidget(self.minimap_widget)
        
        self.sidebar_dock.setWidget(sidebar_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.sidebar_dock)
        self.sidebar_dock.hide()
        
        self._apply_global_style()
        self._show_home()

        self._create_menu()
        self._create_floating_tools()
        
        # Apply theme settings on load
        theme = self.user_data.get_theme_settings()
        if theme.get("dark_mode"):
            self.viewer.toggle_dark_mode(True)
            self.dark_mode_action_menu.setChecked(True)
            self.dark_mode_btn.setChecked(True)
            
    def _apply_global_style(self):
        # A sleek, programmer-focused retro dark mode
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QLabel { color: #d4d4d4; font-family: 'Consolas'; }
            QPushButton {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #d4d4d4;
                padding: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #444444; border-color: #007acc; }
            QPushButton:pressed { background-color: #007acc; color: white; }
            QPushButton:checked { background-color: #007acc; color: white; border-color: #005f9e; }
            QLineEdit, QTextEdit {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                selection-background-color: #264f78;
                font-family: 'Consolas', monospace;
            }
            QDockWidget {
                color: #d4d4d4;
                titlebar-close-icon: url();
                titlebar-normal-icon: url();
            }
            QDockWidget::title {
                background-color: #252526;
                text-align: center;
                padding: 4px;
                border-bottom: 1px solid #3c3c3c;
            }
            QMenuBar { background-color: #333333; color: #d4d4d4; }
            QMenuBar::item:selected { background-color: #444444; }
            QMenu { background-color: #252526; color: #d4d4d4; border: 1px solid #444; }
            QMenu::item:selected { background-color: #062f4a; }
        """)
            
    def _show_home(self):
        recent_files = self.user_data.get_recent_files()
        self.home_widget = HomeWidget(recent_files)
        self.home_widget.file_selected.connect(self.open_file)
        self.setCentralWidget(self.home_widget)

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
        self.dark_mode_action_menu = QAction("Dark Mode", self)
        self.dark_mode_action_menu.setCheckable(True)
        self.dark_mode_action_menu.setChecked(self.user_data.get_theme_settings().get("dark_mode", False))
        self.dark_mode_action_menu.triggered.connect(self._on_dark_mode_toggled)
        view_menu.addAction(self.dark_mode_action_menu)
        
        # Minimap Toggle
        self.minimap_action_menu = QAction("Minimap Options", self)
        self.minimap_action_menu.setCheckable(True)
        self.minimap_action_menu.setChecked(True)
        self.minimap_action_menu.triggered.connect(self._toggle_minimap)
        view_menu.addAction(self.minimap_action_menu)
        
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

    def _create_floating_tools(self):
        # We replace the bulky QToolBar with a sleek Tools frame that stays out of the way
        self.tools_dock = QDockWidget("", self)
        self.tools_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        self.tools_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.tools_dock.setTitleBarWidget(QWidget()) # hide title bar entirely
        
        tools_widget = QWidget()
        layout = QVBoxLayout(tools_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(5, 20, 5, 20)
        
        # Icons via unicode or single characters for minimalism
        self.dark_mode_btn = QPushButton("🌙")
        self.dark_mode_btn.setToolTip("Toggle Dark Mode")
        self.dark_mode_btn.setCheckable(True)
        self.dark_mode_btn.setChecked(self.user_data.get_theme_settings().get("dark_mode", False))
        self.dark_mode_btn.clicked.connect(self._on_dark_mode_toggled)
        
        # Tools
        self.highlight_btn = QPushButton("🖍️")
        self.highlight_btn.setToolTip("Highlighter (Ctrl+H)")
        self.highlight_btn.setCheckable(True)
        self.highlight_btn.clicked.connect(self._toggle_highlight_mode)
        
        self.comment_btn = QPushButton("💬")
        self.comment_btn.setToolTip("Comment Selection")
        self.comment_btn.setCheckable(True)
        self.comment_btn.clicked.connect(self._toggle_comment_mode)
        
        self.eraser_btn = QPushButton("🧽")
        self.eraser_btn.setToolTip("Eraser")
        self.eraser_btn.setCheckable(True)
        self.eraser_btn.clicked.connect(self._toggle_eraser_mode)
        
        # Layout addition
        layout.addWidget(self.dark_mode_btn)
        layout.addSpacing(15)
        layout.addWidget(self.highlight_btn)
        layout.addWidget(self.comment_btn)
        layout.addWidget(self.eraser_btn)
        
        # Brightness slider kept minimal at bottom
        layout.addStretch()
        layout.addWidget(QLabel("🔆"))
        self.brightness_slider = QSlider(Qt.Orientation.Vertical)
        self.brightness_slider.setRange(20, 100) # 0.2 to 1.0
        self.brightness_slider.setValue(int(self.user_data.get_theme_settings().get("brightness", 1.0) * 100))
        self.brightness_slider.setFixedHeight(100)
        self.brightness_slider.valueChanged.connect(self._on_brightness_changed)
        layout.addWidget(self.brightness_slider, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        self.tools_dock.setWidget(tools_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tools_dock)

    def zoom_in(self):
        self.viewer.set_zoom(self.viewer.zoom * 1.2)

    def zoom_out(self):
        self.viewer.set_zoom(self.viewer.zoom / 1.2)

    def _on_brightness_changed(self, value):
        brightness = value / 100.0
        self.user_data.set_theme_setting("brightness", brightness)
        # Update viewer theme without turning off dark mode
        theme = self.user_data.get_theme_settings()
        self.viewer.set_theme_settings(theme)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.Wheel and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            return True
        return super().eventFilter(source, event)

    def _on_dark_mode_toggled(self, checked):
        self.viewer.toggle_dark_mode(checked)
        self.user_data.set_theme_setting("dark_mode", checked)
        self.dark_mode_action_menu.setChecked(checked)
        if hasattr(self, 'dark_mode_btn'):
            self.dark_mode_btn.setChecked(checked)

    def _toggle_highlight_mode(self, checked=None):
        from ui.pdf_label import InteractionMode
        # Handle call from QAction shortcut
        if checked is None:
            checked = not self.highlight_btn.isChecked()
            self.highlight_btn.setChecked(checked)
            
        if checked:
            self.central_label.mode = InteractionMode.HIGHLIGHT
            self.central_label.setCursor(Qt.CursorShape.CrossCursor)
            self.comment_btn.setChecked(False)
            self.eraser_btn.setChecked(False)
        else:
            self.central_label.mode = InteractionMode.NORMAL
            self.central_label.setCursor(Qt.CursorShape.ArrowCursor)

    def _toggle_comment_mode(self, checked):
        from ui.pdf_label import InteractionMode
        if checked:
            self.central_label.mode = InteractionMode.COMMENT
            self.central_label.setCursor(Qt.CursorShape.IBeamCursor)
            self.highlight_btn.setChecked(False)
            self.eraser_btn.setChecked(False)
        else:
            self.central_label.mode = InteractionMode.NORMAL
            self.central_label.setCursor(Qt.CursorShape.ArrowCursor)

    def _toggle_eraser_mode(self, checked):
        from ui.pdf_label import InteractionMode
        if checked:
            self.central_label.mode = InteractionMode.ERASER
            self.central_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self.highlight_btn.setChecked(False)
            self.comment_btn.setChecked(False)
        else:
            self.central_label.mode = InteractionMode.NORMAL
            self.central_label.setCursor(Qt.CursorShape.ArrowCursor)

    def _toggle_minimap(self, checked):
        self.minimap_widget.setVisible(checked)

    def open_file(self, filepath=None):
        if not filepath:
            filepath, _ = QFileDialog.getOpenFileName(
                 self,
                 "Open PDF",
                 "",
                 "PDF Files (*.pdf)"
            )
        if filepath:
            print(f"Opening file: {filepath}")
            self.user_data.add_recent_file(filepath)
            
            # Switch back to scroll area viewer
            self.setCentralWidget(self.scroll_area)
            self.notes_dock.show()
            self.sidebar_dock.show()
            self.viewer.open_document(filepath)
            
            # Restore page progress
            last_page = self.user_data.get_last_read_page(filepath)
            if 0 < last_page < self.viewer.renderer.get_page_count():
                self.viewer.current_page = last_page
                self.viewer.render_current_page()
            
    def document_loaded(self, page_count: int):
        self.setWindowTitle(f"DarkPDF - {page_count} pages")
        
        # Load Minimap
        theme = self.user_data.get_theme_settings()
        is_dark = theme.get("dark_mode", False)
        
        # Helper lambda to pass bboxes fetching safely
        bbox_func = lambda idx, z: self.viewer.renderer.get_page_image_bboxes(idx, z)
        self.minimap_widget.load_minimap(is_dark, bbox_func, theme)
        self.minimap_widget.select_page(self.viewer.current_page)

    def display_page(self, qimage):
        qpixmap = QPixmap.fromImage(qimage)
        self.central_label.setPixmap(qpixmap)
        self.central_label.resize(qpixmap.size())
        
        # Update left sidebar info
        if self.viewer.renderer.doc:
            current = self.viewer.current_page + 1
            total = self.viewer.renderer.get_page_count()
            
            # Update quietly without triggering textChanged / entered events
            self.page_input.blockSignals(True)
            self.page_input.setText(str(current))
            self.page_input.blockSignals(False)
            
            self.total_pages_label.setText(f" / {total}")
            self.minimap_widget.select_page(self.viewer.current_page)
        
        # Save reading progress and load notes
        if self.viewer.renderer.doc:
            doc_path = self.viewer.renderer.doc.name
            self.user_data.set_last_read_page(doc_path, self.viewer.current_page)
            
            note_text = self.user_data.get_note(doc_path, self.viewer.current_page)
            # update UI without triggering save
            self.notes_edit.blockSignals(True)
            self.notes_edit.setPlainText(note_text)
            self.notes_edit.blockSignals(False)

    def _on_notes_changed(self):
        if self.viewer.renderer.doc:
            doc_path = self.viewer.renderer.doc.name
            note_text = self.notes_edit.toPlainText()
            self.user_data.set_note(doc_path, self.viewer.current_page, note_text)

    def _on_highlight_requested(self, rect: QRect):
        if self.viewer.renderer.doc:
            self.viewer.add_highlight(rect)
            
    def _on_erase_requested(self, rect: QRect):
        if self.viewer.renderer.doc:
            self.viewer.erase_highlight(rect)
            
    def _on_comment_requested(self, rect: QRect):
        if self.viewer.renderer.doc:
            # Revert UI scale mapping to get the underlying PDF text
            import fitz
            pdf_rect = fitz.Rect(
                rect.left() / self.viewer.zoom,
                rect.top() / self.viewer.zoom,
                rect.right() / self.viewer.zoom,
                rect.bottom() / self.viewer.zoom
            )
            page = self.viewer.renderer.doc.load_page(self.viewer.current_page)
            words = page.get_text("text", clip=pdf_rect)
            
            # Show the dock if it's hidden and prompt the user to comment on the text
            self.notes_dock.show()
            current_note = self.notes_edit.toPlainText()
            separator = "\n\n" if current_note else ""
            
            extracted = words.strip().replace('\n', ' ')
            if extracted:
                injection = f"{separator}> \"{extracted}\"\n- "
                
                self.notes_edit.blockSignals(True)
                self.notes_edit.setPlainText(current_note + injection)
                self.notes_edit.blockSignals(False)
                
                # Move cursor to end
                cursor = self.notes_edit.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.notes_edit.setTextCursor(cursor)
                self.notes_edit.setFocus()

    def _on_page_input_entered(self):
        try:
            val = int(self.page_input.text().strip())
            # Convert UI 1-index back to 0-index internally
            target_idx = val - 1
            if self.viewer.renderer.doc and 0 <= target_idx < self.viewer.renderer.get_page_count():
                self.viewer.current_page = target_idx
                self.viewer.render_current_page()
            else:
                # Revert if bounds are invalid
                self.page_input.setText(str(self.viewer.current_page + 1))
        except ValueError:
            self.page_input.setText(str(self.viewer.current_page + 1))

    def _on_minimap_page_selected(self, page_index: int):
        if self.viewer.renderer.doc and 0 <= page_index < self.viewer.renderer.get_page_count():
            self.viewer.current_page = page_index
            self.viewer.render_current_page()
