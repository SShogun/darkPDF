from PySide6.QtGui import QImage
import fitz
import numpy as np
from darkmode import apply_dark_mode

def get_qimage(pix: fitz.Pixmap, dark_mode: bool = False, bboxes: list = None, theme: dict = None) -> QImage:
    """Convert PyMuPDF pixmap to PySide6 QImage, applying dark mode if requested."""
    # Convert samples to writable numpy array
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).copy()
    img_array = img_array.reshape(pix.h, pix.w, pix.n)
    
    has_alpha = pix.alpha
    
    # Process through dark mode engine if enabled
    if dark_mode:
        img_array = apply_dark_mode(img_array, has_alpha, bboxes, theme)
        
    # Determine format
    if has_alpha:
        fmt = QImage.Format_RGBA8888
    else:
        fmt = QImage.Format_RGB888
        
    # Create QImage and attach a reference to the numpy array 
    # to prevent it from being garbage collected while the QImage uses it.
    qimg = QImage(img_array.data, pix.w, pix.h, pix.stride, fmt)
    qimg.ndarray = img_array 
    return qimg.copy()
