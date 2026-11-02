# CV Task 2 — Shape Detection and Active Contour (from scratch)

Backend of a web app for Assignment 2:
1. **Canny** edges, then **lines, circles, ellipses** (Hough transforms) drawn on the image.
2. **Active contour (snake)** with the greedy algorithm → **chain code, perimeter, area**.

All image processing is **written from scratch with NumPy**. OpenCV is used only to read / write image
files (and for the mouse window of the command-line snake tool).

| Part | Technology | Job |
|---|---|---|
| `services/` | Python, NumPy | The algorithms (one file per part + one shared file) |
| `schemas/` | Pydantic | The JSON shape of every response (field names, types, units) |
| `api/` | FastAPI | One router per part; receives an image + options, returns JSON |
| `tests/` | pytest | Service tests (bug fixes, expected results of every test image) + API tests |

Detailed explanation of every algorithm: [`docs/TASK2_EXPLAINED.md`](docs/TASK2_EXPLAINED.md).
Code review (bugs found and their status): [`docs/CODE_REVIEW.md`](docs/CODE_REVIEW.md).

---

## 1. How to run

From `CV_task2/`:
```bash
python -m venv venv
venv\Scripts\activate               # Windows
pip install -r requirements.txt     # pinned versions -> reproducible
uvicorn api.main:app --reload       # API on http://127.0.0.1:8000, interactive docs at /docs
python -m pytest tests              # 28 tests, ~1 minute (the ellipse detector is the slow part)
```

Command-line snake (click the contour with the mouse): `python -m services.Active_contour image.png`

---

## 2. Flow

```
 Browser                           api/ (FastAPI)                        services/ (NumPy)
 ───────                           ──────────────                        ─────────────────
 upload image + options  ───►  read_image: file bytes -> BGR uint8   ──►  algorithms
 (multipart form)                                                          return arrays / tuples
                          ◄───  response model (schemas/):           ◄──
 show images + numbers          images -> base64 PNG, tuples -> named JSON objects
```

1. The browser sends the image as a file and the options as form fields (same names and defaults as
   the service functions).
2. `api/utils.read_image` decodes the file to a **BGR uint8** array (OpenCV's order, kept everywhere,
   so no colour conversion is needed).
3. The router calls the service functions.
4. The router fills the response model from `schemas/`: images become base64 PNG strings, shape tuples
   become named objects (e.g. `(cx, cy, r)` → `{"cx": .., "cy": .., "r": ..}`).
5. Errors: a bad image, contour or option inside a service raises `ValueError` → **HTTP 400** with a
   readable message. A wrong type / out-of-range form value → **HTTP 422** (checked by FastAPI).

---

## 3. Project structure

```
CV_task2/
├── services/
│   ├── image_io.py                      shared: decode/encode files, to_gray, Gaussian blur, Sobel gradients, window filters
│   ├── Canny_and_objects_detection.py   Part 1: canny_edge_detector, detect_lines, detect_circles, detect_ellipses, draw_shapes
│   └── Active_contour.py                Part 2: greedy_snake, chain_code, chain_perimeter, chain_area, draw_snake
├── schemas/
│   ├── detection.py                     Line, Circle, Ellipse, ShapesResponse
│   └── snake.py                         Point, POINTS (parses the points field), SnakeResponse
├── api/
│   ├── main.py                          FastAPI app, ValueError -> 400, includes the routers
│   ├── utils.py                         read_image (shared by the routers)
│   └── routers/
│       ├── detection.py                 POST /api/shapes
│       └── snake.py                     POST /api/snake
├── tests/                               test_services.py, test_api.py
├── Test_images/                         9 test images + EXPECTED_RESULTS.txt
├── opencv_comparison.py                 OpenCV versions, only to compare (not used by the API)
├── docs/                                TASK2_EXPLAINED.md, CODE_REVIEW.md
└── requirements.txt                     pinned versions
```

**Dependency rule:** `api` → `schemas` + `services`; `services` never import FastAPI or HTTP code;
both service files take their shared helpers from `image_io.py` only (no copy of any helper).

---

## 4. API reference

Both endpoints are `POST`, take a multipart form (`image` file + options) and return JSON.

### `POST /api/shapes` — Part 1

| Option (default) | Meaning (unit) |
|---|---|
| `low_threshold` 50 · `high_threshold` 150 | Canny thresholds (gradient magnitude; a full 0→255 step gives up to 1020) |
| `sigma` 1.4 | Gaussian blur strength (px); 0 = no blur |
| `detect_lines` / `detect_circles` / `detect_ellipses` true | which detectors run (ellipses take ~3–10 s on 640×480) |
| `threshold` 60 · `min_line_length` 40 · `max_line_gap` 10 | lines: min Hough votes (pixels), min length (px), max gap (px) |
| `min_radius` 10 · `max_radius` empty · `min_votes` 30 | circles: radius range (px; empty = half the image), min votes |
| `min_axis_length` 10 · `max_axis_length` empty · `min_center_votes` 25 | ellipses: min minor axis (px), max major axis (px; empty = image diagonal), min centre votes |
| `min_edge_support` 0.8 | circles + ellipses: fraction of the outline that must lie on edges (0–1) |

Response:
```json
{
  "edges": "<base64 PNG>",  "image": "<base64 PNG, shapes drawn>",
  "lines":    [{"x1": 60, "y1": 330, "x2": 260, "y2": 330}],
  "circles":  [{"cx": 140, "cy": 330, "r": 67}],
  "ellipses": [{"cx": 420, "cy": 330, "width": 220, "height": 121, "angle": 30.1}]
}
```
Units: all coordinates / lengths in px; `width` / `height` = full major / minor axis; `angle` in
degrees (major axis from the x-axis, y down). Colours in `image`: lines green, circles red, ellipses blue.

### `POST /api/snake` — Part 2

| Option (default) | Meaning (unit) |
|---|---|
| `points` (required) | initial contour, JSON list of `[x, y]` (px), at least 3, drawn **around** the object |
| `alpha` 1.0 · `beta` 1.0 · `gamma` 1.2 | weights: continuity · curvature · image (edge) |
| `sigma` 1.4 | blur before the gradient (px) |
| `neighborhood` 3 | odd search window side (px) |
| `spacing` 5.0 | distance between contour points (px) |
| `max_iterations` 500 · `min_moved` 2 | stop after N iterations, or when fewer than `min_moved` points moved |
| `curv_thresh` 0.25 | curvature above which a point on a strong edge is a corner (β = 0 there) |

Response:
```json
{
  "image": "<base64 PNG, final contour drawn>",
  "points":  [[x, y], ...],             "history": [[[x, y], ...], ...],
  "chain_start": [x, y],                "chain_code": [0, 0, 7, 6, ...],
  "perimeter": 411.6,                   "area": 12221.0
}
```
Units: points in px · `perimeter` in px (straight step 1, diagonal √2) · `area` in px² (shoelace on
the chain-code vertices). `history[0]` = initial (resampled) contour, `history[-1]` = final contour,
so iterations = `len(history) - 1` and number of contour points = `len(points)`.

Example (Python):
```python
import requests

with open("Test_images/03_circles_only.png", "rb") as f:
    r = requests.post("http://127.0.0.1:8000/api/snake", files={"image": f},
                      data={"points": "[[40, 40], [200, 40], [200, 200], [40, 200]]"})
print(r.json()["perimeter"], r.json()["area"])
```

---

## 5. Design choices and why

| Choice | Why |
|---|---|
| **One `/api/shapes` endpoint** with `detect_*` switches | All detectors use the same Canny edge map: computed once, not three times. Switches let the UI skip the slow ellipse detector |
| **`schemas/` with Pydantic models** | One clear JSON contract for the frontend; field units shown in `/docs`; shape tuples become named fields |
| **Routers per part** | Part 1 and Part 2 are independent; each file stays small |
| **BGR kept everywhere** | OpenCV reads and writes BGR; the services were written for BGR. No conversion = no colour-swap bugs |
| **Snake returns the full history** | The frontend can animate the snake evolving |
| **No image size limit** | Team decision. Note: ellipse memory grows with image size² (~225 MB per accumulator copy at 2000×1500) |
| **Plain `def` endpoints** | CPU-heavy NumPy work runs in FastAPI's worker threads, so one slow request doesn't block others |
| **No database** | Every request is image in → result out; nothing to store |
| **No CORS** | Same as Task 1: the frontend dev server will proxy `/api/*` to the backend |
