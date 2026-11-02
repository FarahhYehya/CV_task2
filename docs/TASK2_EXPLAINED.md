# CV Task 2 — Full Explanation (for the discussion)

> Goal of this file: understand **every point of the assignment**, **how it is done in our code**, and
> **why**, well enough to defend it in a 30-minute discussion.
> Code files: `services/Canny_and_objects_detection.py` (Part 1), `services/Active_contour.py` (Part 2),
> `services/image_io.py` (helpers shared by both). How to call them over HTTP: `README.md` §4.

---

## 0. The assignment

| # | What is asked | Notes written by the TA on the slide |
|---|---|---|
| 1 | For all given images (gray **and** color): detect edges with the **Canny** edge detector, then detect **lines, circles, ellipses**, and **superimpose** (draw) the detected shapes on the image | "scratch" under Canny → Canny must be written **from scratch**. "Hough transform" over lines / circles. "Paper" next to ellipses → ellipse method should follow a **published paper**. "C++" at the top (meaning to be confirmed with the TA) |
| 2 | Initialize a contour around an object, evolve the **Active Contour Model (snake)** with the **greedy algorithm**, output the result as **chain code**, compute the **perimeter** and the **area** inside the contour | "No. of points of contour" and "radius circle" in a box → the UI should show the **number of contour points** and the **circle radius** |
| — | Deadline | "Two weeks after 1st task submission" |

Everything is written **from scratch with NumPy**. OpenCV is used only to read/write image files and for
the mouse window in the command-line snake tool (and in `opencv_comparison.py`, which is only a
reference to compare against — it is not part of the solution).

---

## 1. Big picture (the flow)

```
 Part 1                                                     Part 2
 ──────                                                     ──────
 image (gray or color)                                      image + initial contour points (clicked)
   │                                                          │
   ▼                                                          ▼
 _to_gray ──► Canny edge map (0/255)                        resample_contour (points every 5 px)
                 │                                            │
      ┌──────────┼──────────────────┐                         ▼
      ▼          ▼                  ▼                       greedy_snake (iterate until stable)
 detect_lines  detect_circles  detect_ellipses                │
 (Hough ρ,θ)   (gradient Hough) (reduced Hough)               ▼
      └──────────┼──────────────────┘                       chain_code ──► chain_perimeter, chain_area
                 ▼                                            │
            draw_shapes (lines green, circles red,            ▼
                         ellipses blue)                     draw_snake
```

**One shared set of helpers** is used by everything. Generic ones are in `services/image_io.py`;
detection-only ones (with `_`) are at the top of `Canny_and_objects_detection.py`:

| Helper | Job | Used by |
|---|---|---|
| `to_gray` | gray / BGR / BGRA → float gray 0–255. Gray = `0.299R + 0.587G + 0.114B` | everything |
| `sliding` / `window_op` | one routine that combines shifted copies of an array: gives Gaussian blur, box sum, max filter, dilation | blur, peaks, "near edge" maps |
| `gaussian_blur` | separable Gaussian, kernel radius = 3σ | Canny, gradients |
| `gradients` | blur + 3×3 Sobel → `gx, gy` | Canny, circles, ellipses, snake |
| `in_bounds` | which (x, y) are inside the image | detectors, drawing, snake |
| `_edge_points` | edge pixels + unit gradient direction at each | circles, ellipses |
| `_pick_peaks` / `_local_maxima` | find the strongest cells of an accumulator | all Hough detectors |
| `_outline_support` | which fraction of a circle/ellipse outline lies on edge pixels | circles, ellipses (verification) |
| `_remove_duplicates` | keep one shape when two are almost the same (inner + outer side of a thick stroke) | circles, ellipses |

---

## 2. Canny edge detector (from scratch)

Function: `canny_edge_detector(image, low_threshold=50, high_threshold=150, sigma=1.4)`
Output: uint8 image, **255 = edge, 0 = not edge**, same size as the input.

| Step | What it does | How in our code | Why |
|---|---|---|---|
| 1. Gaussian smoothing | blur the image | `_gaussian_blur`, σ = 1.4 px, kernel radius = round(3σ) = 4 px (9×9), edge-copy padding | removes noise; without it every noisy pixel becomes an "edge" |
| 2. Gradient | strength and direction of change | 3×3 Sobel → `gx`, `gy`; magnitude `√(gx²+gy²)`; direction `atan2(gy, gx)` | an edge = where brightness changes fast |
| 3. Non-maximum suppression (NMS) | make edges **1 pixel thin** | direction is rounded to 0°, 45°, 90°, 135°; a pixel is kept only if it is ≥ both neighbours **along the gradient** | the gradient is wide (several pixels); we want only its ridge |
| 4. Double threshold | classify pixels | `strong = nms ≥ high`, `weak = nms ≥ low` | one threshold either breaks real edges or keeps noise |
| 5. Hysteresis | keep weak pixels **connected** to strong ones | `_hysteresis`: breadth-first growth from the strong pixels through 8-connected weak pixels | real edges are long and connected; noise is isolated |

**Units:** σ in pixels. Thresholds are in **gradient-magnitude units** (Sobel of a 0–255 image). A full
0 → 255 step gives a Sobel magnitude of up to 1020, so thresholds can be above 255.

---

## 3. Lines — Hough transform (ρ, θ)

Function: `detect_lines(image, edge_image, rho=1, theta=1°, threshold=60, min_line_length=40, max_line_gap=10, max_distance=2.0)`
Output: `[(x1, y1, x2, y2), ...]` line **segments** in pixels.

**Idea:** a line is written as `ρ = x·cosθ + y·sinθ` (ρ = distance from the origin, θ = angle of the
line's normal). A line `y = mx + c` cannot describe vertical lines, ρ-θ can.

| Step | What happens | Code |
|---|---|---|
| 1. Voting | every edge pixel votes for **every (ρ, θ)** line passing through it (θ = 0°…179°, step 1°) | accumulator size = 180 × (2·diagonal+1); done in chunks with `np.bincount` so memory stays small |
| 2. Peaks | a cell with many votes = many edge pixels on the same line | local maxima in a 5×5 window with ≥ `threshold` = 60 votes; the 150 strongest are kept |
| 3. Line → segments | Hough gives infinite lines; the image has segments | take the edge pixels within 2 px of the line, **re-fit** the direction with PCA (undoes the 1° rounding), sort them along the line, cut where the gap > `max_line_gap` (10 px), keep pieces ≥ `min_line_length` (40 px) |
| 4. Straightness check | an arc of a big circle also fits in a 2 px band | the 5th–95th percentile of the across-line distance must be ≤ 2 px |
| 5. Merge | a thick stroke gives 2 parallel lines; a broken line gives pieces | `_merge_similar_lines`: joins segments that are parallel (≤ 5°), close (≤ 10 px) and nearby (gap ≤ 25 px) |

---

## 4. Circles — gradient Hough transform

Function: `detect_circles(image, edge_image, sigma=1.4, min_radius=10, max_radius=None, min_votes=30, min_edge_support=0.8, max_candidates=40)`
Output: `[(cx, cy, r), ...]` in pixels.

**Classic Hough** for circles uses a **3-D accumulator (a, b, r)**: every edge pixel votes for every
centre at every radius → very slow and memory-hungry. Our version uses the **gradient direction**
(Kimme, Ballard & Sklansky 1975, the same idea as OpenCV's `HOUGH_GRADIENT`):

| Step | What happens | Why |
|---|---|---|
| 1. Vote for centres | the centre of a circle lies **on the gradient line** of each edge pixel. Each pixel votes for `p ± r·(gradient direction)` for every r → **2-D accumulator (a, b)** | 2-D instead of 3-D → much less memory and time |
| 2. Candidate centres | accumulator smoothed (3×3 sum), up to 40 peaks with ≥ 30 votes, ≥ 5 px apart | |
| 3. Radius per centre | for each centre: histogram of distances to the edge pixels whose gradient points to/from it (`radial > 0.9`). Each histogram peak = a radius | finds **several radii per centre** → concentric circles work (test image 09) |
| 4. Verification | draw the circle and check that ≥ 80% of its outline lies within 2 px of an edge | removes false circles (e.g. from rectangle corners) |
| 5. Duplicates | inner and outer edge of a thick stroke give 2 circles → keep the best supported | |

---

## 5. Ellipses — reduced-parameter Hough (the "paper" part)

Function: `detect_ellipses(image, edge_image, sigma=1.4, min_axis_length=10, ..., min_edge_support=0.8, angle_step=5)`
Output: `[(cx, cy, width, height, angle_degrees), ...]`; `width` = full major axis, `height` = full minor
axis, `angle` = direction of the major axis from the x-axis (image coordinates, y down).

**Problem:** an ellipse has **5 parameters** (cx, cy, a, b, φ). A 5-D accumulator is impossible
(e.g. 640 × 480 × 300 × 300 × 36 cells). **Solution:** split it into 2-D + 3-D.

| Stage | What happens | Paper idea |
|---|---|---|
| 1. Centre (2-D) | an ellipse is **centrally symmetric**: two edge points with **opposite gradients** (parallel tangents) on opposite sides have the centre as their midpoint. All such pairs vote with their midpoint → peaks = candidate centres | Tsuji & Matsumoto 1978 (parallel tangents → centre) |
| 2. Mirror filter | for a centre c, keep only edge points p whose mirror `2c − p` is also an edge | removes points of other shapes |
| 3. Axes + angle (3-D) | with the centre known only (a, b, φ) remain. For each φ (step 5°) and each a, the point gives `b = |v| / √(1 − u²/a²)` → vote in an (φ, a, b) accumulator | reduced parameter space (the idea also used by Xie & Ji 2002) |
| 4. Refinement | least-squares fit of `Ax² + Bxy + Cy² = 1` on the agreeing points → exact a, b, φ from the eigenvalues/eigenvectors | removes the 5° / 1 px rounding of the accumulator |
| 5. Verification | ≥ 80% of the outline must lie on edges; very flat ones (b < 0.2a) are rejected | |
| 6. Several per centre | the points of the found ellipse are removed and the search repeats (up to 4) | concentric ellipses |
| 7. Not circles | ellipses with minor ≥ 90% of major are removed — they are reported by `detect_circles` | each shape counted **once** |

---

## 6. Superimposing the shapes

`draw_shapes(image, lines, circles, ellipses, thickness=3)` (thickness in px) returns a **BGR** copy of the image with
**lines = green, circles = red (+ centre dot), ellipses = blue**. Gray images are converted to 3
channels first so colours can be drawn.

---

## 7. Active Contour (snake) — greedy algorithm (Williams & Shah, 1992)

Function: `greedy_snake(image, points, alpha=1.0, beta=1.0, gamma=1.2, sigma=1.4, neighborhood=3, spacing=5.0, max_iterations=500, min_moved=2, curv_thresh=0.25)`
Output: `(final_points, history)`: final contour (n × 2, pixels) and the contour after every iteration.

**Initialization:** the user clicks points **around** the object (outside it). `resample_contour`
puts points every `spacing` = 5 px along the clicked polygon (at least 8 points).

**Energy of point vᵢ** (lower = better):

```
E = α·E_cont + β·E_curv + γ·E_img
E_cont = (d_avg − |vᵢ − vᵢ₋₁|)²      keeps the points evenly spaced (d_avg = mean spacing)
E_curv = |vᵢ₋₁ − 2vᵢ + vᵢ₊₁|²        keeps the contour smooth (second derivative)
E_img  = −|∇I|                        pulls the point onto strong edges
```

| Step | What happens |
|---|---|
| 1 | compute the gradient magnitude `|∇I|` of the blurred image once |
| 2 | for each point: try every position in its 3×3 neighbourhood (`neighborhood`), compute the 3 energies |
| 3 | **normalise** each energy to [0, 1] inside the neighbourhood (so α, β, γ are comparable) |
| 4 | move the point to the position with the **lowest total energy** ("greedy" = best local choice) |
| 5 | after the pass: **corners** — where curvature is a local maximum, above `curv_thresh` and on a strong edge (> 40% of max gradient) → β = 0 there, so the snake can make a sharp corner |
| 6 | repeat until fewer than `min_moved` = 2 points moved, or `max_iterations` |

| Parameter | Meaning | Effect when bigger |
|---|---|---|
| α (alpha) | continuity weight | points more evenly spaced |
| β (beta) | curvature weight | smoother, rounder contour, cuts corners |
| γ (gamma) | image (edge) weight | sticks harder to edges, also to noise |
| σ | blur before the gradient, px | edges "felt" from further away, less precise |

**Important:** our snake has no balloon force, so it **shrinks**. The initial contour must be drawn
**outside** the object.

---

## 8. Chain code, perimeter and area

**Freeman 8-direction chain code** (image coordinates, y down):

```
 3  2  1
 4  ·  0        code k = one step of (DX[k], DY[k])
 5  6  7
```

| Function | What it does | Output (unit) |
|---|---|---|
| `_pixel_path` | joins the snake points by straight pixel lines → closed 8-connected pixel path | list of (x, y) pixels |
| `chain_code(points)` | the direction code of every step around the path | `(start_xy, [0..7, ...])` |
| `chain_perimeter(code)` | even code (straight step) = 1, odd code (diagonal) = √2 | pixels (px) |
| `chain_area(start, code)` | rebuild the vertices from the codes, then **shoelace formula** `½|Σ(xᵢyᵢ₊₁ − xᵢ₊₁yᵢ)|` | px² |

Note: the shoelace area is the area of the polygon through the **pixel centres**. For a 20×20-pixel
square it gives 361 px² (19 × 19), not 400 (pixel count). Both definitions are valid; we must state
which one we use.

---

## 9. Measured results (our code, 640×480 test images)

| Image | Lines | Circles | Ellipses | Time: Canny / lines / circles / ellipses (ms) |
|---|---|---|---|---|
| 01_basic_shapes | 5 | 1 | 1 | 104 / 64 / 237 / 2856 |
| 02_lines_only | 5 | 0 | 0 | 76 / 73 / 224 / 9575 |
| 03_circles_only | 0 | 6 | 0 | 76 / 41 / 246 / 6092 |
| 04_ellipses_only | 0 | 0 | 4 | 90 / 55 / 230 / 6250 |
| 05_noisy_colour | 5 | 1 | 1 | 95 / 63 / 221 / 3120 |
| 06_realistic_objects | 6 | 2 | 1 | 92 / 50 / 211 / 4731 |
| 07_no_round_shapes | 12 | 0 | 0 | 85 / 115 / 256 / 7419 |
| 08_gradient_background | 1 | 1 | 1 | 70 / 44 / 181 / 7139 |
| 09_concentric_circles | 0 | 3 | 0 | 68 / 29 / 200 / 2761 |

Counts = number of shapes found. Times in milliseconds on this laptop. The same counts are checked
automatically by `tests/test_services.py` against `Test_images/EXPECTED_RESULTS.txt`.
**Conclusions:** all counts are correct (06 has 6 lines instead of 5 because of a clock hand, ±1 is
expected). Ellipse detection is **30–100× slower** than the others (3–10 s) → matters for the web app.

Snake test (circle of image 03, start = square around it): 128 points, 56 iterations, 0.6 s. The snake
stopped on the outer edge of the black ring (distance to centre 61.8–63.0 px). Chain code: 352 steps,
perimeter 411.6 px (true circle of r = 62.4: 392.1 px → **+5%**, a known bias of 8-direction chain
codes on curves), area 12 221 px² (true: 12 232 px² → **−0.1%**, very accurate).

---

## 10. Questions the TA may ask (with short answers)

| Question | Answer |
|---|---|
| Why blur before Canny? | Derivatives amplify noise; the Gaussian removes it first |
| Why NMS? | The gradient is several pixels wide; NMS keeps only its maximum → thin edges |
| Why 2 thresholds? | One high threshold breaks edges, one low keeps noise; hysteresis keeps weak pixels only if connected to strong ones |
| Why ρ-θ and not y = mx + c? | m is infinite for vertical lines; ρ-θ is bounded |
| Why θ only 0°–180°? | ρ is signed, so θ and θ+180° describe the same line |
| Circle Hough needs 3-D (a, b, r) — why is yours 2-D? | We use the gradient direction: the centre must lie on the gradient line, so we vote only along it and find r afterwards with a histogram |
| How do you get concentric circles? | Several peaks in the radius histogram of one centre |
| Why is a 5-D ellipse Hough impossible, and what did you do? | Memory/time explode. We find the centre first (2-D, symmetric point pairs), then (a, b, φ) in 3-D |
| Is a circle an ellipse? | Yes (a = b). We report it only as a circle, so every shape is counted once |
| What does "greedy" mean in the snake? | Each point moves to the best position in its small neighbourhood, one point at a time — no global optimisation |
| Why normalise the energies? | They have different units/ranges; normalising makes α, β, γ meaningful weights |
| What happens with a big β? | Smooth contour that cuts corners; that is why β = 0 at detected corners |
| Why does the snake need to start outside? | Continuity + curvature shrink it; there is no balloon force to push it outward |
| Chain code perimeter vs true perimeter? | Diagonal steps = √2; on curves it overestimates by ~5% |
| How is the area computed? | Shoelace formula on the chain-code vertices (px²) |
