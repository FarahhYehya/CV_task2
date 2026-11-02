"""
OpenCV reference implementations - used ONLY to compare against
services/Canny_and_objects_detection.py (the from-scratch code).  Not used by the API.
Each function returns the same format as its from-scratch twin.  The clean-up steps that are
not part of the compared algorithms (merging duplicate lines, checking the outline, removing
duplicate shapes, dropping circles from the ellipses) are shared with the from-scratch code so
both sides follow exactly the same rules.
Run from CV_task2/ so that `services` can be imported.
"""
import cv2
import numpy as np
from services.Canny_and_objects_detection import (_merge_similar_lines, _outline_support, _remove_duplicates,
                                                  _remove_circles, _ellipse_error, _rotate)


def _gray(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image


def cv_canny(image, low=50, high=150, sigma=1.4):
    gray = _gray(image)
    return cv2.Canny(cv2.GaussianBlur(gray, (0, 0), sigma) if sigma > 0 else gray, low, high)


def cv_lines(image, edges, threshold=80, min_len=40, max_gap=10):
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold, minLineLength=min_len, maxLineGap=max_gap)
    return [] if lines is None else _merge_similar_lines(np.asarray(lines).reshape(-1, 4))


def cv_circles(image, edges, min_support=0.8):
    found = cv2.HoughCircles(cv2.GaussianBlur(_gray(image), (9, 9), 2), cv2.HOUGH_GRADIENT, dp=1.2,
                             minDist=30, param1=150, param2=40, minRadius=0, maxRadius=0)
    if found is None:
        return []
    near = cv2.dilate(edges, np.ones((5, 5), np.uint8)) > 0
    circles = []
    for cx, cy, r in np.asarray(found).reshape(-1, 3):
        support = _outline_support(near, cx, cy, r, r, 0.0, min_inside=0.25)
        if support is not None and support >= min_support:
            circles.append((int(round(cx)), int(round(cy)), int(round(r))))
    return circles


def cv_ellipses(image, edges, max_err=0.08, min_cov=0.8, min_axis=10):
    """No Hough for ellipses in OpenCV: contours + cv2.fitEllipse, then a quality check."""
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    found = []
    for c in contours:
        if len(c) < 20:
            continue
        (cx, cy), (wd, ht), ang = cv2.fitEllipse(c)
        if min(wd, ht) < min_axis or min(wd, ht) < 0.2 * max(wd, ht):
            continue
        dx, dy = c[:, 0, 0] - cx, c[:, 0, 1] - cy
        err = _ellipse_error(dx, dy, wd / 2, ht / 2, ang).mean()
        u, v = _rotate(dx, dy, np.deg2rad(ang))                       # does the contour go all the way round?
        sectors = ((np.arctan2(v / (ht / 2), u / (wd / 2)) + np.pi) / (2 * np.pi) * 12).astype(int) % 12
        if err <= max_err and len(np.unique(sectors)) / 12 >= min_cov:
            found.append((-err, cx, cy, wd, ht, ang))                 # best fit (smallest error) first
    ellipses = [(int(round(cx)), int(round(cy)), int(round(wd)), int(round(ht)), float(ang))
                for cx, cy, wd, ht, ang in _remove_duplicates(found)]
    return _remove_circles(ellipses)
