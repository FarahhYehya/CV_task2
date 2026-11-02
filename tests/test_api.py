"""
Tests for the API: every endpoint runs, results reach the JSON, errors are 400 / 422.

Run from CV_task2/:
    python -m pytest tests
"""
import base64
import json
import math
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)
IMAGES = Path(__file__).resolve().parent.parent / "Test_images"


def upload(path):
    return {"image": (path.name, path.read_bytes(), "image/png")}


def decode_b64(text):
    """base64 PNG string from the API -> array."""
    return cv2.imdecode(np.frombuffer(base64.b64decode(text), np.uint8), cv2.IMREAD_UNCHANGED)


def ring_png(radius=40, size=120):
    """White image with a black ring of `radius` px around the centre, as PNG bytes."""
    img = np.full((size, size, 3), 255, np.uint8)
    cv2.circle(img, (size // 2, size // 2), radius, (0, 0, 0), 3)
    return {"image": ("ring.png", cv2.imencode(".png", img)[1].tobytes(), "image/png")}


# ---------- /api/shapes ----------

def test_shapes_finds_the_six_circles():
    body = client.post("/api/shapes", files=upload(IMAGES / "03_circles_only.png"),
                       data={"detect_ellipses": "false"}).json()
    assert len(body["circles"]) == 6
    assert body["ellipses"] == []
    assert set(body["circles"][0]) == {"cx", "cy", "r"}
    assert decode_b64(body["image"]).shape == (480, 640, 3)
    assert decode_b64(body["edges"]).shape == (480, 640)


def test_shapes_finds_the_four_ellipses():
    body = client.post("/api/shapes", files=upload(IMAGES / "04_ellipses_only.png"),
                       data={"detect_lines": "false", "detect_circles": "false"}).json()
    assert len(body["ellipses"]) == 4
    assert set(body["ellipses"][0]) == {"cx", "cy", "width", "height", "angle"}


def test_shapes_with_no_detector_returns_only_edges():
    body = client.post("/api/shapes", files=upload(IMAGES / "02_lines_only.png"),
                       data={"detect_lines": "false", "detect_circles": "false", "detect_ellipses": "false"}).json()
    assert body["lines"] == body["circles"] == body["ellipses"] == []
    assert decode_b64(body["edges"]).max() == 255


def test_shapes_bad_image_is_400():
    response = client.post("/api/shapes", files={"image": ("x.png", b"not an image", "image/png")})
    assert response.status_code == 400


def test_shapes_out_of_range_option_is_422():
    response = client.post("/api/shapes", files=upload(IMAGES / "02_lines_only.png"),
                           data={"min_edge_support": "2"})
    assert response.status_code == 422


# ---------- /api/snake ----------

def test_snake_locks_onto_a_ring():
    square = [[10, 10], [110, 10], [110, 110], [10, 110]]
    body = client.post("/api/snake", files=ring_png(), data={"points": json.dumps(square)}).json()
    distances = [math.hypot(x - 60, y - 60) for x, y in body["points"]]
    assert 38 <= min(distances) and max(distances) <= 45                    # on the ring (radius 40 px, 3 px wide)
    assert body["history"][-1] == body["points"]
    assert len(body["chain_code"]) > 0 and set(body["chain_code"]) <= set(range(8))
    r = sum(distances) / len(distances)
    assert abs(body["area"] - math.pi * r * r) / (math.pi * r * r) < 0.05   # area within 5 %
    assert body["perimeter"] > 0


def test_snake_bad_points_is_400():
    response = client.post("/api/snake", files=ring_png(), data={"points": "[[1, 2], [3]]"})
    assert response.status_code == 400


def test_snake_too_few_points_is_400():
    response = client.post("/api/snake", files=ring_png(), data={"points": "[[1, 2], [3, 4]]"})
    assert response.status_code == 400


def test_snake_even_neighborhood_is_400():
    response = client.post("/api/snake", files=ring_png(),
                           data={"points": "[[10, 10], [110, 10], [60, 110]]", "neighborhood": "4"})
    assert response.status_code == 400
