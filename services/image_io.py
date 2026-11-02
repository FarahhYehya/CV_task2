"""
Shared helpers used by every service (Canny_and_objects_detection.py and Active_contour.py).

Image convention for all services:
  - Images are BGR (or grayscale) uint8, exactly as OpenCV reads them.  BGR is kept everywhere,
    so no colour conversion is needed between reading, processing (to_gray) and writing PNGs.
  - Coordinates are image coordinates: x to the right, y down.

OpenCV is used here ONLY to decode / encode image files - never for processing.
"""
import base64

import cv2
import numpy as np

DEFAULT_SIGMA = 1.4      # Gaussian blur strength used everywhere (change it per call with `sigma=`)


# --------------------------------------------------------------------------- #
#  File <-> array (used by the API)
# --------------------------------------------------------------------------- #
def decode_image(data, source="uploaded file"):
    """Image file bytes -> BGR uint8 array (gray files become 3 equal channels)."""
    if not data:
        raise ValueError(f"Could not load image: {source} is empty.")
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not load image: {source}")
    return image


def encode_png(image):
    """BGR (or gray) uint8 array -> base64 PNG string, ready for <img src="data:image/png;base64,...">."""
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Could not encode the result as PNG.")
    return base64.b64encode(buffer.tobytes()).decode("ascii")


# --------------------------------------------------------------------------- #
#  Processing helpers (NumPy only)
# --------------------------------------------------------------------------- #
def to_gray(image):
    """Accept grayscale, BGR or BGRA (any dtype) and return float32 gray in 0..255."""
    if image is None:
        raise ValueError("image is empty")
    image = np.asarray(image)
    if image.size == 0:
        raise ValueError("image is empty")
    # decide on the ORIGINAL dtype: uint8 is already 0..255 and is never stretched
    needs_stretch = image.dtype != np.uint8 and (image.max() > 255 or image.min() < 0 or image.max() <= 1.0)
    image = image.astype(np.float32)
    if needs_stretch:
        lo, hi = float(image.min()), float(image.max())
        image = (image - lo) * (255.0 / (hi - lo)) if hi > lo else np.zeros_like(image)

    if image.ndim == 2:
        return image
    if image.ndim == 3 and image.shape[2] == 1:
        return image[:, :, 0]
    if image.ndim == 3 and image.shape[2] in (3, 4):          # BGR / BGRA
        return 0.114 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.299 * image[:, :, 2]
    raise ValueError("image must be grayscale, BGR or BGRA")


def sliding(arr, radius, axis, op=np.add, weights=None, mode="constant"):
    """
    Combine the (2*radius+1) shifted copies of `arr` along one axis with `op`
    (optionally weighting each shift).  This single routine is the base of the
    Gaussian blur (weights), box sums (np.add), max filters (np.maximum) and
    dilation (np.logical_or).
    """
    pad = [(0, 0)] * arr.ndim
    pad[axis] = (radius, radius)
    padded = np.pad(arr, pad, mode=mode)
    n = arr.shape[axis]
    out = None
    for i in range(2 * radius + 1):
        sl = [slice(None)] * arr.ndim
        sl[axis] = slice(i, i + n)
        piece = padded[tuple(sl)]
        if weights is not None:
            piece = weights[i] * piece
        out = piece.copy() if out is None else op(out, piece)
    return out


def window_op(arr, radius, op, axes=None):
    """Separable (2r+1) window filter (sum / max / or) over `axes` (default: all axes)."""
    for axis in (range(arr.ndim) if axes is None else axes):
        arr = sliding(arr, radius, axis, op)
    return arr


def gaussian_blur(gray, sigma=DEFAULT_SIGMA):
    """Separable Gaussian blur.  sigma <= 0 means 'no blur'."""
    gray = np.asarray(gray, dtype=np.float32)
    if sigma <= 0:
        return gray
    r = max(1, int(round(3 * sigma)))
    x = np.arange(-r, r + 1, dtype=np.float32)
    kernel = np.exp(-(x ** 2) / (2 * sigma ** 2))
    kernel /= kernel.sum()
    blurred = sliding(gray, r, 0, weights=kernel, mode="edge")
    return sliding(blurred, r, 1, weights=kernel, mode="edge")


def gradients(gray, sigma=DEFAULT_SIGMA):
    """Gaussian blur followed by 3x3 Sobel.  Returns (gx, gy)."""
    p = np.pad(gaussian_blur(gray, sigma), 1, mode="edge")
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])
    return gx, gy


def in_bounds(x, y, h, w):
    """Boolean mask: which integer coordinates (x, y) lie inside an h x w image."""
    return (x >= 0) & (x < w) & (y >= 0) & (y < h)
