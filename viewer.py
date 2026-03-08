"""
ViewerController — bridges the PyQt6 UI with an embedded PDF.js viewer
running inside a QWebEngineView, using a custom URL scheme to bypass
Chromium's file:// CORS restrictions.

Dark Mode uses a hybrid approach:
  1. PyMuPDF renders each page with inverted colors → saved to temp PDF
  2. PDF.js loads the dark PDF for full interactivity (text selection, links)
"""

from PyQt6.QtCore import QObject, pyqtSignal, QUrl, QTimer, QByteArray, QThread
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineUrlScheme,
    QWebEngineUrlSchemeHandler,
    QWebEngineUrlRequestJob,
    QWebEngineProfile,
    QWebEngineSettings,
)
import os
import mimetypes
from pathlib import Path

from darkmode import generate_dark_pdf, get_dark_pdf_cache_path


# ── Custom URL Scheme Handler ──────────────────────────────────

SCHEME_NAME = b"darkpdf"


def register_scheme():
    """Call this ONCE before QApplication() to register the custom scheme."""
    scheme = QWebEngineUrlScheme(SCHEME_NAME)
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Path)
    scheme.setFlags(
        QWebEngineUrlScheme.Flag.SecureScheme
        | QWebEngineUrlScheme.Flag.LocalScheme
        | QWebEngineUrlScheme.Flag.LocalAccessAllowed
        | QWebEngineUrlScheme.Flag.CorsEnabled
    )
    QWebEngineUrlScheme.registerScheme(scheme)


class LocalFileSchemeHandler(QWebEngineUrlSchemeHandler):
    """Serves local files through the darkpdf:// scheme.

    URL layout:
      darkpdf://viewer/web/viewer.html   →  <pdfjs_root>/web/viewer.html
      darkpdf://pdffile/<abs_path>       →  reads the absolute file path
    """

    def __init__(self, pdfjs_root: Path, parent=None):
        super().__init__(parent)
        self.pdfjs_root = pdfjs_root

    def requestStarted(self, job: QWebEngineUrlRequestJob):
        url = job.requestUrl()
        host = url.host()
        path = url.path()

        if host == "viewer":
            local_path = self.pdfjs_root / path.lstrip("/")
        elif host == "pdffile":
            raw_path = path
            if len(raw_path) > 2 and raw_path[0] == '/' and raw_path[2] == ':':
                raw_path = raw_path[1:]
            local_path = Path(raw_path)
        else:
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return

        local_path_str = str(local_path)

        if not os.path.isfile(local_path_str):
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return

        mime_type, _ = mimetypes.guess_type(local_path_str)
        if mime_type is None:
            mime_type = "application/octet-stream"

        try:
            from PyQt6.QtCore import QFile, QIODevice
            f = QFile(local_path_str, job)
            if f.open(QIODevice.OpenModeFlag.ReadOnly):
                job.reply(QByteArray(mime_type.encode()), f)
            else:
                job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)
        except Exception:
            job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)


# ── Background Dark PDF Generator ─────────────────────────────

class DarkPDFWorker(QThread):
    """Generates a dark-mode PDF in a background thread."""
    finished = pyqtSignal(str)   # emits the path to the dark PDF
    progress = pyqtSignal(str)   # emits status messages
    error = pyqtSignal(str)

    def __init__(self, input_path: str, output_path: str, brightness: float = 0.85):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.brightness = brightness

    def run(self):
        try:
            self.progress.emit("Generating dark mode PDF...")
            result = generate_dark_pdf(self.input_path, self.output_path, self.brightness)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ── ViewerController ──────────────────────────────────────────

class ViewerController(QObject):
    document_loaded = pyqtSignal(int)
    page_changed = pyqtSignal(int)
    dark_mode_started = pyqtSignal()      # show loading overlay
    dark_mode_ready = pyqtSignal()         # hide loading overlay
    dark_mode_error = pyqtSignal(str)

    def __init__(self, web_view: QWebEngineView):
        super().__init__()
        self.web_view = web_view
        self.current_page = 0
        self.zoom = 1.0
        self.brightness = 1.0
        self.dark_mode = False
        self.current_filepath = ""
        self._dark_pdf_path = ""
        self._load_connected = False
        self.scroll_timer = None
        self._worker = None

        # Paths
        base_dir = Path(__file__).parent.absolute()
        self.pdfjs_root = base_dir / "ui" / "pdfjs_viewer"

        # Install the custom scheme handler on the default profile
        profile = QWebEngineProfile.defaultProfile()
        self._scheme_handler = LocalFileSchemeHandler(self.pdfjs_root, self)
        profile.installUrlSchemeHandler(QByteArray(SCHEME_NAME), self._scheme_handler)

        # Allow local content and JS
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

    # ── Dark Mode ─────────────────────────────────────────────

    def toggle_dark_mode(self, enabled: bool):
        if not self.current_filepath:
            self.dark_mode = enabled
            return

        self.dark_mode = enabled

        if enabled:
            # Check if we already have a cached dark PDF
            cache_path = get_dark_pdf_cache_path(self.current_filepath)
            if os.path.exists(cache_path):
                # Already cached! Just swap immediately
                self._dark_pdf_path = cache_path
                self._load_pdf_in_viewer(cache_path)
                return

            # Need to generate — kick off background worker
            self.dark_mode_started.emit()
            self._worker = DarkPDFWorker(self.current_filepath, cache_path)
            self._worker.finished.connect(self._on_dark_pdf_ready)
            self._worker.error.connect(self._on_dark_pdf_error)
            self._worker.start()
        else:
            # Switch back to original PDF
            self._load_pdf_in_viewer(self.current_filepath)

    def _on_dark_pdf_ready(self, dark_path: str):
        self._dark_pdf_path = dark_path
        self._load_pdf_in_viewer(dark_path)
        self.dark_mode_ready.emit()
        self._worker = None

    def _on_dark_pdf_error(self, error_msg: str):
        print(f"Dark mode error: {error_msg}")
        self.dark_mode = False
        self.dark_mode_error.emit(error_msg)
        self.dark_mode_ready.emit()
        self._worker = None

    def set_theme_settings(self, theme: dict):
        """Handle brightness changes instantly via CSS filter."""
        if "brightness" in theme:
            self.brightness = theme["brightness"]
            self._apply_brightness()

    def _apply_brightness(self):
        js = f"document.body.style.filter = 'brightness({self.brightness})';"
        if self.web_view.page():
            self.web_view.page().runJavaScript(js)

    # ── Document Loading ──────────────────────────────────────

    def open_document(self, filepath: str, initial_page: int = 0):
        if not os.path.exists(filepath):
            return

        self.current_filepath = filepath
        self.current_page = initial_page
        self._dark_pdf_path = ""

        # Stop any existing timer
        if self.scroll_timer:
            self.scroll_timer.stop()

        # If dark mode is active, check for cached dark version
        if self.dark_mode:
            cache_path = get_dark_pdf_cache_path(filepath)
            if os.path.exists(cache_path):
                self._dark_pdf_path = cache_path
                self._load_pdf_in_viewer(cache_path, initial_page)
                return
            else:
                # Generate dark version
                self.dark_mode_started.emit()
                self._worker = DarkPDFWorker(filepath, cache_path)
                self._worker.finished.connect(lambda p: self._on_dark_pdf_ready_with_page(p, initial_page))
                self._worker.error.connect(self._on_dark_pdf_error)
                self._worker.start()
                return

        self._load_pdf_in_viewer(filepath, initial_page)

    def _on_dark_pdf_ready_with_page(self, dark_path: str, initial_page: int):
        self._dark_pdf_path = dark_path
        self._load_pdf_in_viewer(dark_path, initial_page)
        self.dark_mode_ready.emit()
        self._worker = None

    def _load_pdf_in_viewer(self, filepath: str, page: int = None):
        """Load a PDF file into the PDF.js viewer."""
        if page is None:
            page = self.current_page

        pdf_url = "darkpdf://pdffile/" + filepath.replace("\\", "/")
        viewer_url = f"darkpdf://viewer/web/viewer.html?file={pdf_url}#page={page + 1}"

        if not self._load_connected:
            self.web_view.loadFinished.connect(self._on_load_finished)
            self._load_connected = True

        self.web_view.load(QUrl(viewer_url))

    def _on_load_finished(self, ok: bool):
        if not ok:
            return

        # Hide PDF.js' own toolbar (we have our own controls)
        js_hide = """
        (function() {
            var tb = document.getElementById('toolbarContainer');
            if (tb) tb.style.display = 'none';
            var vc = document.getElementById('viewerContainer');
            if (vc) vc.style.top = '0px';
        })();
        """
        self.web_view.page().runJavaScript(js_hide)
        self._apply_brightness()

        # Poll for page count (PDF.js may take a moment to parse)
        QTimer.singleShot(800, self._query_page_count)

        # Start page-scroll polling
        if self.scroll_timer:
            self.scroll_timer.stop()
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self._poll_current_page)
        self.scroll_timer.start(500)

    def _query_page_count(self):
        js = "typeof PDFViewerApplication !== 'undefined' ? PDFViewerApplication.pagesCount : 0;"
        self.web_view.page().runJavaScript(js, self._on_page_count)

    def _on_page_count(self, count):
        if count and int(count) > 0:
            self.document_loaded.emit(int(count))
        else:
            QTimer.singleShot(500, self._query_page_count)

    # ── Page Polling ──────────────────────────────────────────

    def _poll_current_page(self):
        js = "typeof PDFViewerApplication !== 'undefined' ? PDFViewerApplication.page : 0;"
        self.web_view.page().runJavaScript(js, self._on_page_polled)

    def _on_page_polled(self, page_num):
        if page_num:
            idx = int(page_num) - 1
            if idx != self.current_page:
                self.current_page = idx
                self.page_changed.emit(self.current_page)

    # ── Navigation ────────────────────────────────────────────

    def next_page(self):
        self.web_view.page().runJavaScript("PDFViewerApplication.page++;")

    def prev_page(self):
        self.web_view.page().runJavaScript("PDFViewerApplication.page--;")

    def go_to_page(self, page_1indexed: int):
        self.web_view.page().runJavaScript(f"PDFViewerApplication.page = {page_1indexed};")

    # ── Zoom ──────────────────────────────────────────────────

    def set_zoom(self, new_zoom: float):
        self.zoom = max(0.25, min(new_zoom, 5.0))
        js = f"""
        if (typeof PDFViewerApplication !== 'undefined' && PDFViewerApplication.pdfViewer) {{
            PDFViewerApplication.pdfViewer.currentScaleValue = {self.zoom};
        }}
        """
        self.web_view.page().runJavaScript(js)
