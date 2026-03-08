"""
ViewerController — bridges the PyQt6 UI with an embedded PDF.js viewer
running inside a QWebEngineView, using a custom URL scheme to bypass
Chromium's file:// CORS restrictions.
"""

from PyQt6.QtCore import QObject, pyqtSignal, QUrl, QTimer, QByteArray
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineUrlScheme,
    QWebEngineUrlSchemeHandler,
    QWebEngineUrlRequestJob,
    QWebEngineProfile,
    QWebEnginePage,
    QWebEngineSettings,
)
from PyQt6.QtWidgets import QApplication
import os
import mimetypes
from pathlib import Path


# ── Custom URL Scheme Handler ──────────────────────────────────
# Must be registered BEFORE QApplication is created.

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

        # Determine the local file to serve
        if host == "viewer":
            # Map to the pdfjs_viewer directory
            # path starts with /, so strip it
            local_path = self.pdfjs_root / path.lstrip("/")
        elif host == "pdffile":
            # The absolute file path is encoded in the URL path
            # On Windows, the path starts with /C:/... so strip leading /
            raw_path = path
            if len(raw_path) > 2 and raw_path[0] == '/' and raw_path[2] == ':':
                raw_path = raw_path[1:]  # strip leading /
            local_path = Path(raw_path)
        else:
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return

        local_path_str = str(local_path)

        if not os.path.isfile(local_path_str):
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return

        # Guess MIME type
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


# ── ViewerController ──────────────────────────────────────────

class ViewerController(QObject):
    document_loaded = pyqtSignal(int)
    page_changed = pyqtSignal(int)

    def __init__(self, web_view: QWebEngineView):
        super().__init__()
        self.web_view = web_view
        self.current_page = 0
        self.zoom = 1.0
        self.dark_mode = False
        self.current_filepath = ""
        self._load_connected = False
        self.scroll_timer = None

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
        self.dark_mode = enabled
        self._apply_dark_mode_css()

    def set_theme_settings(self, theme: dict):
        # Only brightness is relevant now — we handle it via CSS opacity
        brightness = theme.get("brightness", 1.0)
        js = f"document.getElementById('viewerContainer').style.opacity = {brightness};"
        self.web_view.page().runJavaScript(js)

    def _apply_dark_mode_css(self):
        if self.dark_mode:
            css = "html { filter: invert(90%) hue-rotate(180deg) !important; } img, canvas { filter: invert(100%) hue-rotate(180deg) !important; }"
        else:
            css = "html { filter: none !important; } img, canvas { filter: none !important; }"

        js = f"""
        (function() {{
            var s = document.getElementById('darkpdf-theme');
            if (!s) {{ s = document.createElement('style'); s.id = 'darkpdf-theme'; document.head.appendChild(s); }}
            s.textContent = `{css}`;
        }})();
        """
        self.web_view.page().runJavaScript(js)

    # ── Document Loading ──────────────────────────────────────

    def open_document(self, filepath: str, initial_page: int = 0):
        if not os.path.exists(filepath):
            return

        self.current_filepath = filepath
        self.current_page = initial_page

        # Stop any existing timer
        if self.scroll_timer:
            self.scroll_timer.stop()

        # Build the custom-scheme URL for the PDF file
        # On Windows, filepath is like C:\foo\bar.pdf → darkpdf://pdffile/C:/foo/bar.pdf
        pdf_url = "darkpdf://pdffile/" + filepath.replace("\\", "/")

        # Build the viewer URL
        viewer_url = f"darkpdf://viewer/web/viewer.html?file={pdf_url}#page={initial_page + 1}"

        # Connect loadFinished only once
        if not self._load_connected:
            self.web_view.loadFinished.connect(self._on_load_finished)
            self._load_connected = True

        self.web_view.load(QUrl(viewer_url))

    def _on_load_finished(self, ok: bool):
        if not ok:
            return

        # Apply dark mode CSS
        self._apply_dark_mode_css()

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
            # Retry after a short delay — PDF might still be loading
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
