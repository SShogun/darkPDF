# DarkPDF 🌙

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-Qt-brightgreen.svg)](https://doc.qt.io/qtforpython/)
[![PyMuPDF](https://img.shields.io/badge/PyMuPDF-PDF-red.svg)](https://pymupdf.readthedocs.io/en/latest/)

**DarkPDF** is a highly optimized, cross-platform desktop application explicitly designed to make long reading sessions at night a comfortable and distraction-free experience. 

By avoiding simple screen dimming and instead utilizing a blazing-fast localized rendering pipeline, DarkPDF converts the blistering white backgrounds of complex textbooks and documents into soothing darkness while seamlessly preserving the crispness of text anti-aliasing and the original color depth of embedded images and photos.

---

## ✨ Key Features

### 🚀 Smart Inversion Engine
Built directly upon `NumPy` array math and 8-bit unsigned transformations, DarkPDF achieves near-zero latency rendering even on highly complex documents. 
- **Image Protection:** DarkPDF identifies and protects physical images and diagrams inside the text boundaries from being inverted, so they always look natural while you read.
- **Auto-Scanned Page Heuristics:** The engine smartly detects scanned documents (where the entire page is technically an image) and forcefully adapts them so you aren't blinded.
- **Granular Brightness Control:** You have full control over the contrast and brightness of the inversion matrix directly from the toolbar slider.

### 📚 Robust Annotations & Persistent State
Read and review documents how you actually want to:
- **Smart Highlighter:** Drag a box over any text, and DarkPDF parses the textual bounds to inject a lightweight transparent annotation directly into the PDF. Native highlight colors are perfectly inverted to a smooth orange when you are in Dark Mode.
    - **Eraser Mode:** Made a mistake? Quickly scrub it away with the native Eraser interactions.
- **Undo Stack:** Hit `Ctrl + Z` to instantly revert any highlighting or erasing mistakes up to 20 steps back.
- **Intelligent Comment Quoter:** Notice something interesting? Select the text on the page using Comment Mode, and DarkPDF immediately extracts the underlying document text, opens your floating Notes dock, and creates a formatted quote for you to respond to. 

### 🧭 Unrivaled Navigation
- **Home Dashboard:** Start up immediately with a populated list of your recent files.
- **Auto-resumption:** Opening a document automatically leaps you forward to the exact page you were on last session!
- **Interactive Minimap:** A scrollable Minimap populates on the sidebar, letting you instantly jump through entire chapters of a document visually.
- **Smooth Zooming:** Use `Ctrl + Scroll` to fluently dive into complex equations or back out.

---

## 🛠️ Technical Stack

DarkPDF pairs the rendering accuracy of modern libraries with the UI flexibility of Qt:

- **Core Application:** `Python`
- **Frontend / UI:** `PySide6` (Qt 6)
- **PDF Operations & Rendering:** `PyMuPDF (fitz)`
- **Image Mathematics:** `NumPy`

---

## 📦 Installation & Usage

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/DarkPDF.git
   cd DarkPDF
   ```

2. **Set up a Virtual Environment (Recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install PySide6 PyMuPDF numpy pytest
   ```

4. **Run Tests (Optional):**
   ```bash
   python -m pytest tests/ -v
   ```

5. **Launch DarkPDF!**
   ```bash
   python main.py
   ```

---

## 🖥️ Keyboard Controls

| Action | Shortcut |
|--------|----------|
    | Open File | `Ctrl + O` |
| Highlighter Tool | `Ctrl + H` |
| Eraser Tool | `Ctrl + E` |
| Undo Last Action | `Ctrl + Z` |
| Toggle Dark Mode | `Ctrl + D` |
| Toggle Notes | `Ctrl + N` |
| Home Dashboard | `Ctrl + Home` |
| Zoom In | `Ctrl + =` |
| Zoom Out | `Ctrl + -` |
| Fast Zoom | `Ctrl + Scroll Wheel` |
| Next/Prev Page | `Right Arrow` / `Left Arrow` |

---

*Because reading code and textbooks at 2 AM shouldn't hurt.*
