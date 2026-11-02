# CV Task 2 — Code Review Report

Reviewed: `Canny_and_objects_detection.py`, `Active_contour.py`, `opencv_comparison.py`,
`Test_images/EXPECTED_RESULTS.txt`, `README.md`.
Method: read every function, then **ran** the code on all 9 test images and on small hand-made cases
(scripts in section 6). Line numbers in sections 1–3 refer to the **original** files (before they were
moved to `services/`). What was fixed afterwards: **section 5**.

**Overall verdict:** the algorithms are **correct** and give the right results on all test images
(see `TASK2_EXPLAINED.md` §9). The problems below are **bugs on edge cases, a broken file, wrong
documentation, speed, and clean-code issues** — not wrong algorithms.

Severity: 🔴 bug (wrong result / crash) · 🟠 concept issue (works, but must be understood or fixed for the web app) · 🟡 clean code.

---

## 1. Bugs 🔴

| # | Where | Problem | Proof (ran it) | Fix |
|---|---|---|---|---|
| B1 | `opencv_comparison.py:11` | Imports from `image_processing`, which **does not exist** (the file is `Canny_and_objects_detection.py`) | `ModuleNotFoundError: No module named 'image_processing'` → the file cannot run at all | Fix the import (or move this file to `tests/` as a reference check) |
| B2 | `Canny_and_objects_detection.py:43-44` (`_to_gray`) | `image.astype(np.float32)` runs **before** `if image.dtype != np.uint8`, so the check is always true. Any uint8 image whose max ≤ 1 is **stretched** to 0–255 | uint8 mask `[[0,1],[1,0]]` → `[[0,255],[255,0]]` | Read the dtype before the cast |
| B3 | `Active_contour.py:132` (`_pixel_path`) / `chain_code` | Crashes when the contour collapses to one pixel (or `points` is empty) | `chain_code([(5,5),(5,5),(5,5)])` → `IndexError: list index out of range` | Validate: at least 3 distinct points; raise a clear `ValueError` |
| B4 | `Test_images/EXPECTED_RESULTS.txt` | Says "every circle shows up in BOTH the circle and the ellipse counts", but the code **removes circles from the ellipses** (`_remove_circles`). The expected ellipse column is wrong for 6 of 9 images. It also names a file `image_processing.py` | Real ellipse counts: 1, 0, 0, 4, 1, 1, 0, 1, 0 (expected file says 2, 0, 6, 4, 2, 3, 0, 2, 3) | Update the file to match the code |
| B5 | `Canny_and_objects_detection.py:563` (`draw_shapes`) | `r = thickness // 2` → thickness 2 and 3 draw the **same** 3-px line; even thicknesses are impossible | thickness 1→1 row, 2→3, 3→3, 4→5 | Document "thickness = 2r+1" or take a radius |
| B6 | `Canny_and_objects_detection.py:561` (`draw_shapes`) | `astype(np.uint8)` on a float image **wraps** values > 255 (e.g. 300 → 44) | by reading | Clip before the cast |

---

## 2. Concept issues 🟠 (must be understood / decided)

| # | Where | Issue | Why it matters |
|---|---|---|---|
| C1 | `detect_ellipses` | **Slow**: 2.8–9.6 s per 640×480 image (others ≤ 0.26 s). The (φ, a, b) accumulator grows with image size²: ~23 MB per copy at 640×480, ~92 MB at 1280×960, ~225 MB at 2000×1500 (3 copies exist while smoothing) | In a web app a big photo can take minutes or run out of memory → need a **max image size / downscale** decision |
| C2 | `canny_edge_detector` | Thresholds 50 / 150 are **absolute** gradient values. For a low-contrast image the same numbers find almost nothing | Option: relative thresholds (fraction of the max gradient). Decision for the UI |
| C3 | `detect_lines:304` | Uses `canny_edge_detector(image)` **without `sigma`**, while circles/ellipses pass `sigma` → inconsistent API | When the API computes Canny once and passes `edge_image`, this disappears |
| C4 | `detect_lines:335, 341, 349` | Compares a **pixel count** with `min_line_length` (a **length**). A diagonal line has ~0.71 pixels per px of length → diagonal lines must be ~41% longer to pass | Small bias against diagonal lines; mention if asked |
| C5 | `detect_circles` | On a thick stroke it returns the radius of **one side** of the stroke (inner or outer edge), not the middle | Circle in image 03: detected r = 57 px, snake found the outer edge at 62 px → a 5 px difference is expected, not a bug |
| C6 | Module docstring | Cites **Xie & Ji 2002**, but the method used (parallel-tangent pairs → centre, then 3-D (a, b, φ)) is the **Tsuji & Matsumoto 1978** idea. Xie & Ji pick 2 points as the **major-axis ends** and vote for b in a **1-D** accumulator | The TA wrote "Paper" — be ready to say exactly which paper the method follows |
| C7 | `_refine_ellipse` | Refines a, b, φ but **not the centre** (integer from the accumulator) | ±1 px centre error; fine for drawing |
| C8 | `greedy_snake` | No balloon force → the snake only **shrinks**; it must be initialised **outside** the object | Must be explained in the UI ("draw around the object") |
| C9 | `chain_perimeter` / `chain_area` | 8-direction chain perimeter **overestimates curves by ~5%** (411.6 vs 392.1 px). Area = shoelace on pixel centres: a 20×20-pixel square gives 361 px², pixel count gives 400 | Both are standard, but the report/UI must say which definition is used |
| C10 | `select_contour_by_hand` | Uses an OpenCV window — **cannot work in a web backend** | In the web app the clicks come from the browser; the backend only receives the points |
| C11 | Several | Magic numbers tuned on the test images: stroke tolerance 13 px (`:192`), 150 line peaks (`:327`), 5000 sampled points (`:426`), 0.98 / 0.12 / 0.15 / 12 votes in the ellipse code | Real photos may need other values; at least name them as constants |

---

## 3. Clean-code issues 🟡

| # | Where | Issue | Fix |
|---|---|---|---|
| K1 | `Active_contour.py:34` | Imports **private** helpers (`_gradients`, `_in_bounds`, `_to_gray`) from another module. They are really **shared** helpers | Move shared helpers to one shared module (like Task 1's `image_io.py`), public names |
| K2 | Docstrings | The same file has 3 names: `Canny_and_objects_detection.py`, `shape_detection.py` (`Active_contour.py:5`), `image_processing.py` (`opencv_comparison.py:2`, expected-results file) | One name everywhere |
| K3 | `canny_edge_detector:227, 230` | `_to_gray(image)` is computed **twice** | Compute once, reuse |
| K4 | All detectors | The gradient (blur + Sobel) is computed **3 times per image** (Canny, circles, ellipses) | Acceptable (~30 ms each); could pass it in |
| K5 | `detect_lines:325` | Comment says "accumulator lightly smoothed along rho" — **no smoothing is done** | Fix the comment |
| K6 | `opencv_comparison.py:3` | Comment "Do not send this file to your teammate" | Remove |
| K7 | Project | No `requirements.txt`, no tests, `README.md` is empty (`# CV_task2`) | Add them (backend step) |
| K8 | `detect_lines` | Parameter `image` is unused when `edge_image` is given | Fine for now; a clear order is "edges first, image optional" |

**Good points (keep them):** fully vectorised NumPy (fast for pure Python), one `_sliding` routine
reused for blur / max / dilate (no repeated code), deterministic (fixed random seed), clear docstrings,
every shape verified against the edge map (few false positives).

---

## 4. Summary

| Category | Count | Most important |
|---|---|---|
| 🔴 Bugs | 6 | B1 broken import, B2 gray conversion, B3 chain-code crash, B4 wrong expected results |
| 🟠 Concepts | 11 | C1 ellipse speed/memory, C6 which paper, C8 snake must start outside |
| 🟡 Clean code | 8 | K1 private helpers imported across files, K2 three names for one file |

---

## 5. Status after the backend ticket ✅

Decisions taken with the team: fix all bugs + K1/K3, layout = Task 1 + `schemas/`, no image size
limit, snake returns the iteration history.

| # | Status | How it was fixed | Proved by |
|---|---|---|---|
| B1 | ✅ fixed | import changed to `services.Canny_and_objects_detection` | file imports without error |
| B2 | ✅ fixed | `to_gray` decides `needs_stretch` on the **original** dtype, then casts | `test_to_gray_does_not_stretch_uint8`, `test_to_gray_still_stretches_float_0_to_1` |
| B3 | ✅ fixed | `resample_contour` rejects < 3 (x, y) points; `_pixel_path` rejects a contour of < 2 pixels → `ValueError` (HTTP 400) | `test_chain_code_of_collapsed_contour_is_a_clear_error`, `test_snake_needs_three_points`, `test_snake_too_few_points_is_400` |
| B4 | ✅ fixed | `EXPECTED_RESULTS.txt` ellipse column = real ellipses only (1, 0, 0, 4, 1, 1, 0, 1, 0) | `test_test_image_counts` (all 9 images) |
| B5 | ✅ fixed | `thickness` = exact width in px; default changed 2 → 3 so drawings look **identical** to before | `test_draw_thickness_is_exact` |
| B6 | ✅ fixed | `np.clip` before `astype(np.uint8)` | `test_draw_clips_instead_of_wrapping` |
| K1 | ✅ fixed | shared helpers moved to `services/image_io.py` as public names (`to_gray`, `gradients`, `in_bounds`, `gaussian_blur`, `sliding`, `window_op`, `DEFAULT_SIGMA`) | both services import only from there |
| K2 | ✅ fixed | docstrings now name the real files | — |
| K3 | ✅ fixed | gray computed once in `canny_edge_detector` | — |
| K5 | ✅ fixed | comment now says what the code does (5×5 local maxima, strongest 150) | — |
| K6 | ✅ fixed | comment removed | — |
| K7 | ✅ fixed | `requirements.txt` (pinned), `tests/` (28 tests), `README.md` | fresh venv + `pip install -r` + all tests pass |
| extra | ✅ added | `greedy_snake` rejects an even or < 3 `neighborhood` (it silently used a bigger window) | `test_snake_even_neighborhood_is_400` |
| C1–C11, K4, K8 | ⏳ open | concept points for the discussion / later decisions (C1 speed, C2 relative thresholds, C3 `detect_lines` sigma, C6 paper name, …) | — |

**Results unchanged:** after the refactor, the overlay and edge images of all 9 test images are
**pixel-identical** to the original code, and the snake test gives the same numbers (56 iterations,
352 chain steps, 411.6 px, 12 221 px²).

**Files changed:** `Canny_and_objects_detection.py` and `Active_contour.py` (moved to `services/`,
fixes above), `opencv_comparison.py`, `Test_images/EXPECTED_RESULTS.txt`, `README.md`, `.gitignore`
(+ `.pytest_cache/`). **New:** `services/image_io.py`, `schemas/detection.py`, `schemas/snake.py`,
`api/main.py`, `api/utils.py`, `api/routers/detection.py`, `api/routers/snake.py`,
`tests/test_services.py`, `tests/test_api.py`, `requirements.txt`, `docs/`.

---

## 6. Commands run

Review commands were run with Task 1's virtual environment (`numpy 2.5.4`, `opencv 5.0.0`); scripts
live in the session scratchpad, not in the project.

```bash
# 1. list project files
find . -type f
# 2. read Task 1 architecture (api/, services/, tests/)
cat requirements.txt api/main.py services/image_io.py services/edges.py tests/test_api.py
# 3. check Python + packages
venv/Scripts/python.exe -c "import numpy, cv2, fastapi"
# 4. run all detectors on the 9 test images, save overlays, measure time
venv/Scripts/python.exe verify_detection.py <CV_task2> <out_dir>
# 5. run the snake + chain code, and reproduce bugs B1-B5 and memory of C1
venv/Scripts/python.exe verify_snake.py <CV_task2> <out_dir>
```

Backend build (from `CV_task2/`):
```bash
# 6. move the algorithm files into services/ keeping git history
git mv Canny_and_objects_detection.py services/ ; git mv Active_contour.py services/
# 7. fresh virtual environment from the pinned requirements (reproducibility check)
python -m venv venv ; venv/Scripts/python.exe -m pip install -r requirements.txt
# 8. all tests
venv/Scripts/python.exe -m pytest tests
# 9. outputs of all 9 images compared pixel by pixel with the original code's outputs
# 10. OpenAPI paths/schemas + one /api/snake call through FastAPI's TestClient
```
