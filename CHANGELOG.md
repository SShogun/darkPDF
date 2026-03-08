# Version History / Changelog

This document tracks all features, architectural changes, and bug fixes applied to DarkPDF.

## [v2.0.0] - PDF.js Engine Migration (`pdfjs-engine` branch)
- **BREAKING** Replaced the entire PyMuPDF image-rendering engine with an embedded Chromium browser running Mozilla PDF.js v4.
- **BREAKING** Migrated from PySide6 to PyQt6 (+ PyQt6-WebEngine) for WebEngine compatibility on Python 3.13.
- **Added** a custom `darkpdf://` URL scheme handler (`LocalFileSchemeHandler`) to bypass Chromium's `file://` CORS restrictions.
- **Added** native text selection, hyperlink clicking, and searchability — all handled natively by PDF.js.
- **Changed** Dark Mode to CSS filter injection (`invert(90%) hue-rotate(180deg)`) instead of NumPy pixel manipulation.
- **Changed** Brightness control to CSS opacity instead of NumPy channel scaling.
- **Removed** PyMuPDF dependency (`fitz`), `renderer.py`, `darkmode.py`, `image_utils.py`, `pdf_label.py`.
- **Removed** Python-side highlight, eraser, and comment annotation tools (now handled natively by PDF.js).
- **Removed** Minimap widget (incompatible with WebEngine architecture).

## [v1.5.0] - Stability, Testing, & Undo Mechanics
- **Added** an internal 20-step Undo Stack! Pressing `Ctrl + Z` seamlessly restores previous annotation states (Highlights & Erases).
- **Added** Interactive Clickable PDF Links! DarkPDF now supports Native PDF Hyperlinks (both internal page jumping and external URI browser opening). Cursor changes automatically when hovering over interactive text.
- **Added** a comprehensive Automated Test Suite (53 Tests) using `pytest` covering the `ViewerController`, `UserDataManager`, `PDFRenderer`, and `MainWindow` GUI.
- **Redesigned** the Toolbar UI into a sleek, labeled vertical dock mimicking modern IDE layouts for better readability without losing screen real-estate.
- **Added** explicit global keyboard shortcuts, including `Ctrl+Z` (Undo), `Ctrl+N` (Toggle Notes), `Ctrl+E` (Eraser), `Ctrl+D` (Dark Mode), and `Ctrl+Home` (Home Screen).
- **Added** a dynamic Zoom slider ranging from 25% to 300%.
- **Fixed** a critical dangling reference crash where opening a PDF, returning to the Home Screen, and reopening the PDF would instantly kill the app due to `setCentralWidget` actively destroying the `QScrollArea`. Resolved natively by migrating to a `QStackedWidget` layout core.
- **Fixed** the "Resume Reading" auto-resumption bug. PyMuPDF renders were quietly overwriting the tracked page progress array upon opening. Opening files now correctly restores your last-read page directly without overwriting `index 0`.

## [v1.4.0] - UI Refinement & Interactive Tools
- **Moved** Navigation sidebar and Minimap entirely to the Right Side of the window for better layout coherence next to the notes.
- **Added** an Eraser mode logic! Users can now drag a box over existing annotations to remove them from the underlying PyMuPDF instance.
- **Fixed** overlapping text rendering on the inner sidebar buttons (`< Prev`).
- **Added** visual toggle to make the Minimap an optional, hideable UI element.
- **Fixed** a file I/O bug where PyMuPDF `Coder=4` repaired files would crash the renderer upon trying to auto-save incrementally.
- **Tweaked** Highlighting native colors so that they render as a brilliant, visible Orange when inverted in Dark Mode.

## [v1.3.0] - Interactive Reading & Annotation Engine 
- **Added** a multi-mode Interaction layer on the Document Viewer.
- **Added** a physical Highlighter! Drawing bounding boxes dynamically maps to the PDF's text scale, searches for precise layout strings, and adds native highlight annotations to the open PDF.
- **Added** an Interactive Comment extractor! Drawing bounding boxes over sentences now parses the document text directly underneath it, snaps open the Notes sidebar, and quotes the author so users can begin typing a note immediately.
- **Added** the Toolbar Brightness Slider that feeds into the Numpy equation.
- **Added** `Ctrl + Scroll` dynamic zooming mechanics.

## [v1.2.0] - Smart Inversion & Persistent User Data
- **Created** `UserDataManager` which handles saving and loading a `settings.json` file natively in the user's `~/.darkpdf` system folder.
- **Added** a Clean Home Page Dashboard widget showing all `Recent Files`. 
- **Added** reading progress tracking that automatically leaps users back to the page they last observed when unlocking a document.
- **Added** a persistent cross-document Note-taking sidebar dock. Notes are saved per page and persist cleanly.
- **Added** Image Bounding Box Extraction: Images and layout photos are no longer inverted into scary negative colors.
- **Added** Scanned Page Heuristics: if an image comprises >80% of a page's size, DarkPDF recognizes it as a book scan and applies the inversion anyway.

## [v1.1.0] - The Core Math & Dark Mode
- **Created** the `apply_dark_mode` function utilizing rapid fire 8-bit unsigned integer math on numpy arrays.
- **Hooked up** the internal PDF pixmap extraction directly to the inverse numpy arrays while preserving document alpha layers.
- **Added** Basic zoom and page navigation actions and keyboard shortcuts.

## [v1.0.0] - Initial Prototype Base
- **Added** Base desktop window framing using `PySide6`.
- **Added** internal `PDFRenderer` class leaning upon `PyMuPDF (fitz)` to open and hold `pdf` file streams in memory.
- **Added** basic display of document matrix maps to UI labels.
