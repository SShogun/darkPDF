import numpy as np

def apply_dark_mode(img_array: np.ndarray, has_alpha: bool, bboxes: list = None, theme: dict = None) -> np.ndarray:
    """
    Convert light PDF pages into dark themed pages.
    """
    channels = img_array.shape[2]
    
    if has_alpha and channels == 4:
        rgb = img_array[:, :, :3]
        alpha = img_array[:, :, 3:]
    else:
        rgb = img_array
        alpha = None

    # Pre-copy Original RGB for image regions restoration
    original_rgb = rgb.copy() if bboxes else None

    # Fast 8-bit unsigned integer math inversion
    inverted_rgb = 255 - rgb
    
    # Theme adjustments (brightness/contrast) map to dark colors
    if theme:
        brightness = theme.get("brightness", 1.0)
        # brightness scale on inverted image:
        # Since it's UI dark mode, lowering brightness means making the dark background darker
        # i.e multiplying inverted pixels by a factor. But actually we want the background (originally white -> now black) 
        # to stay black, and text (originally black -> now white) to be dimmed.
        # Wait, simple brightness scaling on inverted image:
        # np.clip(inverted_rgb * brightness, 0, 255).astype(np.uint8)
        if brightness != 1.0:
            inverted_rgb = np.clip(inverted_rgb * brightness, 0, 255).astype(np.uint8)
    
    # Restore images
    if bboxes:
        h, w = rgb.shape[:2]
        page_area = h * w
        
        for bbox in bboxes:
            x0, y0, x1, y1 = bbox
            x0, y0 = max(0, int(x0)), max(0, int(y0))
            x1, y1 = min(w, int(x1)), min(h, int(y1))
            
            # Scanned page heuristic: if an image takes more than 80% of page, invert it anyway
            img_area = (x1 - x0) * (y1 - y0)
            if img_area > 0.8 * page_area:
                continue # leave it inverted
            
            if x1 > x0 and y1 > y0:
                inverted_rgb[y0:y1, x0:x1] = original_rgb[y0:y1, x0:x1]
    
    if alpha is not None:
        return np.concatenate([inverted_rgb, alpha], axis=2)
    return inverted_rgb
