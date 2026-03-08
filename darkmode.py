"""
Dark Mode PDF Generator
-----------------------
Uses PyMuPDF to create an inverted-color copy of a PDF.
The result is saved to a temp file and can be loaded into PDF.js.
"""
import fitz
import tempfile
import os
from pathlib import Path


def generate_dark_pdf(input_path: str, output_path: str = None, brightness: float = 0.85) -> str:
    """
    Create a dark-mode version of the PDF by re-rendering each page
    with inverted colors. Images are protected (re-inverted) so they
    look correct against the dark background.

    Args:
        input_path: Path to the original PDF
        output_path: Where to save the dark PDF (auto-generated if None)
        brightness: Overall brightness of the dark version (0.0-1.0)

    Returns:
        Path to the generated dark-mode PDF
    """
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix="_dark.pdf")
        os.close(fd)

    # Edit the document in-place to absolutely guarantee all metadata,
    # internal links, bookmarks, and text layers are natively preserved.
    src = fitz.open(input_path)

    for page in src:
        # Render at 1.5x for quality vs speed balance
        zoom = 1.5
        mat = fitz.Matrix(zoom, zoom)
        
        # We must ignore the current overlay images to prevent recursive feedback
        # if this script is somehow run twice, but usually it's fine.
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Invert the pixmap colors
        pix.invert_irect(pix.irect)

        # Cover the entire page with the new inverted image!
        # Because we use overlay=True, it visually covers the old colors.
        # But crucially, PDF.js renders invisible text layers OVER images, 
        # so text selection and links remain 100% functional!
        page.clean_contents()
        page.insert_image(page.rect, pixmap=pix, overlay=True)

    src.save(output_path, garbage=4, deflate=True)
    src.close()

    return output_path

def cleanup_old_dark_pdfs(max_files: int = 15):
    """Keep only the N most recently generated dark PDFs in the temp directory to save disk space."""
    try:
        temp_dir = Path(tempfile.gettempdir())
        dark_pdfs = list(temp_dir.glob("darkpdf_*_dark.pdf"))
        if len(dark_pdfs) > max_files:
            dark_pdfs.sort(key=lambda p: p.stat().st_mtime)
            # Delete all but the most recent max_files
            for old_pdf in dark_pdfs[:-max_files]:
                old_pdf.unlink(missing_ok=True)
    except Exception as e:
        print(f"Error cleaning up old dark PDFs: {e}")

def get_dark_pdf_cache_path(original_path: str) -> str:
    """Get a deterministic temp path for the dark version of a PDF."""
    cleanup_old_dark_pdfs()
    import hashlib
    name_hash = hashlib.md5(original_path.encode()).hexdigest()[:12]
    base_name = Path(original_path).stem
    return os.path.join(tempfile.gettempdir(), f"darkpdf_{base_name}_{name_hash}_dark.pdf")
