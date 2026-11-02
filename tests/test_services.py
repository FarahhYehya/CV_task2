"""
Tests for the services: the bug fixes of docs/CODE_REVIEW.md and the expected results of every
test image (Test_images/EXPECTED_RESULTS.txt).

Run from CV_task2/:
    python -m pytest tests
"""
from pathlib import Path

import cv2
import numpy as np
import pytest

from services import Canny_and_objects_detection as detection
from services.Active_contour import chain_area, chain_code, chain_perimeter, greedy_snake
from services.image_io import to_gray

IMAGES = Path(__file__).resolve().parent.parent / "Test_images"


def expected_rows():
    """EXPECTED_RESULTS.txt -> [(file name, lines, circles, ellipses)]."""
    rows = []
    for line in (IMAGES / "EXPECTED_RESULTS.txt").read_text().splitlines():
        parts = line.split()
        if parts and parts[0].endswith(".png"):
            rows.append((parts[0], int(parts[1]), int(parts[2]), int(parts[3])))
    return rows


# ---------- every test image gives the expected shape counts (reproducibility) ----------

@pytest.mark.parametrize("name, n_lines, n_circles, n_ellipses", expected_rows())
def test_test_image_counts(name, n_lines, n_circles, n_ellipses):
    image = cv2.imread(str(IMAGES / name))
    edges = detection.canny_edge_detector(image)
    assert abs(len(detection.detect_lines(image, edges)) - n_lines) <= 1     # lines are +/- 1 (see the file)
    assert len(detection.detect_circles(image, edges)) == n_circles
    assert len(detection.detect_ellipses(image, edges)) == n_ellipses


# ---------- bug fixes (docs/CODE_REVIEW.md) ----------

def test_to_gray_does_not_stretch_uint8():                     # B2
    mask = np.array([[0, 1], [1, 0]], dtype=np.uint8)
    assert to_gray(mask).tolist() == [[0.0, 1.0], [1.0, 0.0]]


def test_to_gray_still_stretches_float_0_to_1():               # B2 (the intended case still works)
    assert to_gray(np.array([[0.0, 1.0]])).tolist() == [[0.0, 255.0]]


def test_chain_code_of_collapsed_contour_is_a_clear_error():   # B3
    with pytest.raises(ValueError, match="single pixel"):
        chain_code([(5, 5), (5, 5), (5, 5)])


def test_snake_needs_three_points():                           # B3
    with pytest.raises(ValueError, match="at least 3"):
        greedy_snake(np.zeros((50, 50), np.uint8), [(1, 1), (10, 10)])


@pytest.mark.parametrize("thickness", [1, 2, 3, 4])
def test_draw_thickness_is_exact(thickness):                    # B5
    out = detection.draw_shapes(np.zeros((20, 20), np.uint8), lines=[(2, 10, 17, 10)], thickness=thickness)
    assert np.any(out[:, :, 1] > 0, axis=1).sum() == thickness


def test_draw_clips_instead_of_wrapping():                       # B6
    out = detection.draw_shapes(np.full((4, 4), 300.0))
    assert out.max() == 255


# ---------- chain code on a known shape ----------

def test_chain_code_of_square():
    start, code = chain_code([(10, 10), (29, 10), (29, 29), (10, 29)])   # 20 x 20 pixels
    assert chain_perimeter(code) == 76.0                                   # 4 sides x 19 steps (px)
    assert chain_area(start, code) == 361.0                                # 19 x 19 (px^2, pixel centres)
