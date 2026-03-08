from PySide6.QtWidgets import (QMainWindow, QFileDialog, QLabel, QScrollArea, QToolBar, 
    QSlider, QDockWidget, QTextEdit, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, 
    QLineEdit, QStackedWidget)
from PySide6.QtGui import QAction, QPixmap, QShortcut, QKeySequence
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

        # ── Central Stacked Widget (prevents widget destruction on view switch) ──
        self.stacked = QStackedWidget(self)
        self.setCentralWidget(self.stacked)
        
        # Page 0: Home Widget (placeholder — rebuilt each time)
        self._home_placeholder = QWidget()
        self.stacked.addWidget(self._home_placeholder)
        
        # Page 1: PDF Viewer (scroll area + label)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.central_label = PDFViewerLabel()
        self.central_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.central_label.highlight_requested.connect(self._on_highlight_requested)
        self.central_label.comment_requested.connect(self._on_comment_requested)
        self.central_label.erase_requested.connect(self._on_erase_requested)
        self.scroll_area.setWidget(self.central_label)
        self.stacked.addWidget(self.scroll_area)
        
        # Install event filter for Ctrl+scroll zooming
        self.scroll_area.installEventFilter(self)
        self.scroll_area.viewport().installEventFilter(self)
        
        # Create Notes Dock Widget (hidden by default, toggled via toolbar)
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
        self.sidebar_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        
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
        self._create_keyboard_shortcuts()
        
        # Apply theme settings on load
        theme = self.user_data.get_theme_settings()
        if theme.get("dark_mode"):
            self.viewer.toggle_dark_mode(True)
            self.dark_mode_action_menu.setChecked(True)
            self.dark_mode_btn.setChecked(True)
            
    def _apply_global_style(self):
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
            QSlider::groove:horizontal {
                height: 6px;
                background: #3c3c3c;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #007acc;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::groove:vertical {
                width: 6px;
                background: #3c3c3c;
                border-radius: 3px;
            }
            QSlider::handle:vertical {
                background: #007acc;
                height: 14px;
                margin: 0 -4px;
                border-radius: 7px;
            }
        """)
            
    def _show_home(self):
        """Switch to the home view."""
        recent_files = self.user_data.get_recent_files()
        self.home_widget = HomeWidget(recent_files)
        self.home_widget.file_selected.connect(self.open_file)
        
        # Replace page 0 in stacked widget
        old = self.stacked.widget(0)
        self.stacked.removeWidget(old)
        old.deleteLater()
        self.stacked.insertWidget(0, self.home_widget)
        self.stacked.setCurrentIndex(0)

    def _go_home(self):
        """Return to the home page, hiding PDF-related panels."""
        self.sidebar_dock.hide()
        self.notes_dock.hide()
        if hasattr(self, 'notes_btn'):
            self.notes_btn.setChecked(False)
        self.setWindowTitle("DarkPDF")
        self._show_home()

    def _create_menu(self):
        menu_bar = self.menuBar()
        
        # File Menu
        file_menu = menu_bar.addMenu("File")

        open_action = QAction("Open PDF", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        home_action = QAction("Home", self)
        home_action.triggered.connect(self._go_home)
        file_menu.addAction(home_action)
        
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

    def _create_keyboard_shortcuts(self):
        """Register global keyboard shortcuts on the main window."""
        # Ctrl+H — Toggle Highlighter
        shortcut_highlight = QShortcut(QKeySequence("Ctrl+H"), self)
        shortcut_highlight.activated.connect(self._toggle_highlight_mode)
        
        # Ctrl+D — Toggle Dark Mode
        shortcut_dark = QShortcut(QKeySequence("Ctrl+D"), self)
        shortcut_dark.activated.connect(lambda: self._on_dark_mode_toggled(not self.dark_mode_btn.isChecked()))
        
        # Ctrl+N — Toggle Notes Panel
        shortcut_notes = QShortcut(QKeySequence("Ctrl+N"), self)
        shortcut_notes.activated.connect(self._toggle_notes)
        
        # Ctrl+E — Toggle Eraser
        shortcut_eraser = QShortcut(QKeySequence("Ctrl+E"), self)
        shortcut_eraser.activated.connect(lambda: self._toggle_eraser_mode(not self.eraser_btn.isChecked()))
        
        # Ctrl+Home — Go to Home
        shortcut_home = QShortcut(QKeySequence("Ctrl+Home"), self)
        shortcut_home.activated.connect(self._go_home)
        
        # Ctrl+Z — Undo
        shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        shortcut_undo.activated.connect(self._on_undo)

    def _create_floating_tools(self):
        # Sleek left-side toolbar
        self.tools_dock = QDockWidget("", self)
        self.tools_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        self.tools_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.tools_dock.setTitleBarWidget(QWidget()) # hide title bar entirely
        
        tools_widget = QWidget()
        layout = QVBoxLayout(tools_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(5, 15, 5, 15)
        layout.setSpacing(4)
        
        # Helper to create labeled tool buttons
        def make_tool_btn(icon_text, label_text, tooltip, checkable=False):
            btn = QPushButton(f"{icon_text}  {label_text}")
            btn.setToolTip(tooltip)
            btn.setCheckable(checkable)
            btn.setMinimumWidth(110)
            btn.setStyleSheet("text-align: left; padding: 6px 8px;")
            return btn
        
        # Home button at the very top
        self.home_btn = make_tool_btn("🏠", "Home", "Go to Home Page (Ctrl+Home)")
        self.home_btn.clicked.connect(self._go_home)
        layout.addWidget(self.home_btn)
        
        layout.addSpacing(10)
        
        # Dark mode toggle
        self.dark_mode_btn = make_tool_btn("🌙", "Dark", "Toggle Dark Mode (Ctrl+D)", checkable=True)
        self.dark_mode_btn.setChecked(self.user_data.get_theme_settings().get("dark_mode", False))
        self.dark_mode_btn.clicked.connect(self._on_dark_mode_toggled)
        layout.addWidget(self.dark_mode_btn)
        
        layout.addSpacing(10)
        
        # --- Annotation Tools ---
        tools_label = QLabel("─── Tools ───")
        tools_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tools_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(tools_label)
        
        self.highlight_btn = make_tool_btn("🖍️", "Highlight", "Highlighter (Ctrl+H)", checkable=True)
        self.highlight_btn.clicked.connect(self._toggle_highlight_mode)
        layout.addWidget(self.highlight_btn)
        
        self.comment_btn = make_tool_btn("💬", "Comment", "Comment Selection", checkable=True)
        self.comment_btn.clicked.connect(self._toggle_comment_mode)
        layout.addWidget(self.comment_btn)
        
        self.eraser_btn = make_tool_btn("🧽", "Eraser", "Eraser (Ctrl+E)", checkable=True)
        self.eraser_btn.clicked.connect(self._toggle_eraser_mode)
        layout.addWidget(self.eraser_btn)
        
        # Notes toggle button
        self.notes_btn = make_tool_btn("📝", "Notes", "Toggle Notes Panel (Ctrl+N)", checkable=True)
        self.notes_btn.clicked.connect(self._toggle_notes)
        layout.addWidget(self.notes_btn)
        
        # Undo button
        self.undo_btn = make_tool_btn("↩️", "Undo", "Undo Last Action (Ctrl+Z)")
        self.undo_btn.clicked.connect(self._on_undo)
        layout.addWidget(self.undo_btn)
        
        # --- Zoom Section ---
        layout.addStretch()
        
        zoom_label = QLabel("─── Zoom ───")
        zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        zoom_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(zoom_label)
        
        self.zoom_value_label = QLabel("100%")
        self.zoom_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_value_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #007acc;")
        layout.addWidget(self.zoom_value_label)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(25, 300)  # 25% to 300%
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(110)
        self.zoom_slider.setToolTip("Zoom Level (Ctrl+= / Ctrl+-)")
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        layout.addWidget(self.zoom_slider, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # --- Brightness Section ---
        layout.addSpacing(10)
        
        bright_label = QLabel("── Brightness ──")
        bright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bright_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(bright_label)
        
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(20, 100) # 0.2 to 1.0
        self.brightness_slider.setValue(int(self.user_data.get_theme_settings().get("brightness", 1.0) * 100))
        self.brightness_slider.setFixedWidth(110)
        self.brightness_slider.setToolTip("Brightness")
        self.brightness_slider.valueChanged.connect(self._on_brightness_changed)
        layout.addWidget(self.brightness_slider, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        self.tools_dock.setWidget(tools_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.tools_dock)

    # ── Zoom ─────────────────────────────────────────────────────

    def zoom_in(self):
        new_zoom = self.viewer.zoom * 1.2
        self.viewer.set_zoom(new_zoom)
        self._sync_zoom_slider()

    def zoom_out(self):
        new_zoom = self.viewer.zoom / 1.2
        self.viewer.set_zoom(new_zoom)
        self._sync_zoom_slider()

    def _sync_zoom_slider(self):
        """Sync the zoom slider and label to match the viewer's current zoom."""
        percent = int(self.viewer.zoom * 100)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(max(25, min(300, percent)))
        self.zoom_slider.blockSignals(False)
        self.zoom_value_label.setText(f"{percent}%")

    def _on_zoom_slider_changed(self, value):
        """Handle user dragging the zoom slider."""
        new_zoom = value / 100.0
        self.viewer.set_zoom(new_zoom)
        self.zoom_value_label.setText(f"{value}%")

    def _on_brightness_changed(self, value):
        brightness = value / 100.0
        self.user_data.set_theme_setting("brightness", brightness)
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

    # ── Undo ─────────────────────────────────────────────────────

    def _on_undo(self):
        self.viewer.undo()

    # ── Mode Toggles ─────────────────────────────────────────────

    def _on_dark_mode_toggled(self, checked):
        self.viewer.toggle_dark_mode(checked)
        self.user_data.set_theme_setting("dark_mode", checked)
        self.dark_mode_action_menu.setChecked(checked)
        if hasattr(self, 'dark_mode_btn'):
            self.dark_mode_btn.setChecked(checked)

    def _toggle_highlight_mode(self, checked=None):
        from ui.pdf_label import InteractionMode
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

    def _toggle_eraser_mode(self, checked=None):
        from ui.pdf_label import InteractionMode
        if checked is None:
            checked = not self.eraser_btn.isChecked()
        self.eraser_btn.setChecked(checked)
        if checked:
            self.central_label.mode = InteractionMode.ERASER
            self.central_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self.highlight_btn.setChecked(False)
            self.comment_btn.setChecked(False)
        else:
            self.central_label.mode = InteractionMode.NORMAL
            self.central_label.setCursor(Qt.CursorShape.ArrowCursor)

    def _toggle_notes(self, checked=None):
        """Toggle the notes dock panel visibility."""
        if checked is None:
            checked = not self.notes_dock.isVisible()
        self.notes_dock.setVisible(checked)
        if hasattr(self, 'notes_btn'):
            self.notes_btn.setChecked(checked)

    def _toggle_minimap(self, checked):
        self.minimap_widget.setVisible(checked)

    # ── File Operations ──────────────────────────────────────────

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
            
            # Restore page progress BEFORE opening so it isn't overwritten
            last_page = self.user_data.get_last_read_page(filepath)
            
            self.user_data.add_recent_file(filepath)
            
            # Switch to PDF viewer (page 1 of stacked widget)
            self.stacked.setCurrentIndex(1)
            self.sidebar_dock.show()
            self.viewer.open_document(filepath, initial_page=last_page)
            
    def document_loaded(self, page_count: int):
        self.setWindowTitle(f"DarkPDF - {page_count} pages")
        
        # Load Minimap
        theme = self.user_data.get_theme_settings()
        is_dark = theme.get("dark_mode", False)
        
        bbox_func = lambda idx, z: self.viewer.renderer.get_page_image_bboxes(idx, z)
        self.minimap_widget.load_minimap(is_dark, bbox_func, theme)
        self.minimap_widget.select_page(self.viewer.current_page)

    def display_page(self, qimage):
        qpixmap = QPixmap.fromImage(qimage)
        self.central_label.setPixmap(qpixmap)
        self.central_label.resize(qpixmap.size())
        
        # Update sidebar info
        if self.viewer.renderer.doc:
            current = self.viewer.current_page + 1
            total = self.viewer.renderer.get_page_count()
            
            self.page_input.blockSignals(True)
            self.page_input.setText(str(current))
            self.page_input.blockSignals(False)
            
            self.total_pages_label.setText(f" / {total}")
            self.minimap_widget.select_page(self.viewer.current_page)
        
        # Sync zoom slider
        self._sync_zoom_slider()
        
        # Save reading progress and load notes
        if self.viewer.renderer.doc:
            doc_path = self.viewer.renderer.doc.name
            self.user_data.set_last_read_page(doc_path, self.viewer.current_page)
            
            note_text = self.user_data.get_note(doc_path, self.viewer.current_page)
            self.notes_edit.blockSignals(True)
            self.notes_edit.setPlainText(note_text)
            self.notes_edit.blockSignals(False)

    # ── Callbacks ────────────────────────────────────────────────

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
            import fitz
            pdf_rect = fitz.Rect(
                rect.left() / self.viewer.zoom,
                rect.top() / self.viewer.zoom,
                rect.right() / self.viewer.zoom,
                rect.bottom() / self.viewer.zoom
            )
            page = self.viewer.renderer.doc.load_page(self.viewer.current_page)
            words = page.get_text("text", clip=pdf_rect)
            
            self.notes_dock.show()
            if hasattr(self, 'notes_btn'):
                self.notes_btn.setChecked(True)
            current_note = self.notes_edit.toPlainText()
            separator = "\n\n" if current_note else ""
            
            extracted = words.strip().replace('\n', ' ')
            if extracted:
                injection = f"{separator}> \"{extracted}\"\n- "
                
                self.notes_edit.blockSignals(True)
                self.notes_edit.setPlainText(current_note + injection)
                self.notes_edit.blockSignals(False)
                
                cursor = self.notes_edit.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                self.notes_edit.setTextCursor(cursor)
                self.notes_edit.setFocus()

    def _on_page_input_entered(self):
        try:
            val = int(self.page_input.text().strip())
            target_idx = val - 1
            if self.viewer.renderer.doc and 0 <= target_idx < self.viewer.renderer.get_page_count():
                self.viewer.current_page = target_idx
                self.viewer.render_current_page()
            else:
                self.page_input.setText(str(self.viewer.current_page + 1))
        except ValueError:
            self.page_input.setText(str(self.viewer.current_page + 1))

    def _on_minimap_page_selected(self, page_index: int):
        if self.viewer.renderer.doc and 0 <= page_index < self.viewer.renderer.get_page_count():
            self.viewer.current_page = page_index
            self.viewer.render_current_page()
