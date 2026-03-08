import numpy as np

def apply_dark_mode(img_array: np.ndarray, has_alpha: bool) -> np.ndarray:
    """
    Convert light PDF pages into dark themed pages.
    
    This function processes the image as a NumPy array.
    Using an inversion method perfectly preserves anti-aliasing on text 
    while meeting the requirement to darken bright backgrounds and lighten dark text.
    """
    channels = img_array.shape[2]
    
    if has_alpha and channels == 4:
        rgb = img_array[:, :, :3]
        alpha = img_array[:, :, 3:]
    else:
        rgb = img_array
        alpha = None

    # Fast 8-bit unsigned integer math inversion
    inverted_rgb = 255 - rgb
    
    if alpha is not None:
        return np.concatenate([inverted_rgb, alpha], axis=2)
    return inverted_rgb
