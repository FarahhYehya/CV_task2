"""
Active Contour Model (snake) - greedy algorithm, implemented from scratch (NumPy only).
The contour is initialised BY HAND (mouse clicks); OpenCV is used only for the window / clicks.

Re-uses the shared helpers (image_io.py: to_gray, gradients, in_bounds, DEFAULT_SIGMA)
and draw_shapes of part 1 (Canny_and_objects_detection.py).

Main functions
--------------
resample_contour(points, spacing)                -> evenly spaced closed contour (n x 2 float array)
greedy_snake(image, points, ...)                 -> (final_points, history)   Williams & Shah greedy snake
chain_code(points)                               -> (start_xy, [0..7, ...])   8-direction Freeman chain code
chain_perimeter(code)                            -> perimeter  (even codes = 1, odd codes = sqrt(2))
chain_area(start_xy, code)                       -> area enclosed by the chain code (shoelace on its vertices)
draw_snake(image, points)                        -> image with the contour drawn on it (via draw_shapes)
select_contour_by_hand(image)                    -> clicked points  (needs OpenCV window)

Greedy snake (Williams & Shah, 1992): every point v_i moves to the position in its
(2k+1)x(2k+1) neighbourhood that minimises
        E = alpha * E_cont + beta * E_curv + gamma * E_img
    E_cont = (d_avg - |v_i - v_{i-1}|)^2        keeps the points evenly spaced
    E_curv = |v_{i-1} - 2 v_i + v_{i+1}|^2      keeps the contour smooth
    E_img  = -|grad I|                          pulls the points onto strong edges
Each term is normalised to [0, 1] in the neighbourhood.  Beta is set to 0 at sharp corners that lie
on an edge.  Iterate until almost no point moves.

Chain code (Freeman, 8 directions, image coordinates: x right, y down):
        3  2  1
        4  .  0          code k = step (DX[k], DY[k])
        5  6  7
"""
import numpy as np

from .Canny_and_objects_detection import draw_shapes
from .image_io import DEFAULT_SIGMA, gradients, in_bounds, to_gray

# Freeman 8-direction steps: index = code
DX = np.array([1, 1, 0, -1, -1, -1, 0, 1])
DY = np.array([0, -1, -1, -1, 0, 1, 1, 1])


# --------------------------------------------------------------------------- #
#  Contour helpers
# --------------------------------------------------------------------------- #
def resample_contour(points, spacing=5.0):
    """Closed polygon through `points` -> points placed every `spacing` px along its length."""
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 3:
        raise ValueError("points must be at least 3 (x, y) pairs")
    closed = np.vstack([pts, pts[:1]])
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(closed, axis=0).T))]
    t = np.linspace(0, s[-1], max(8, int(round(s[-1] / spacing))), endpoint=False)
    return np.stack([np.interp(t, s, closed[:, 0]), np.interp(t, s, closed[:, 1])], axis=1)


def _corner_points(pts, grad, curv_thresh, grad_thresh):
    """Boolean mask of points that are curvature maxima, sharp, and lying on a strong edge."""
    u = np.roll(pts, -1, axis=0) - pts
    u /= np.maximum(np.hypot(u[:, 0], u[:, 1]), 1e-6)[:, None]
    curv = np.sum((u - np.roll(u, 1, axis=0)) ** 2, axis=1)
    x, y = np.rint(pts[:, 0]).astype(int), np.rint(pts[:, 1]).astype(int)
    on_image = in_bounds(x, y, *grad.shape)
    g = np.where(on_image, grad[np.clip(y, 0, grad.shape[0] - 1), np.clip(x, 0, grad.shape[1] - 1)], 0)
    peak = (curv > np.roll(curv, 1)) & (curv > np.roll(curv, -1))
    return peak & (curv > curv_thresh) & (g > grad_thresh)


# --------------------------------------------------------------------------- #
#  Greedy snake
# --------------------------------------------------------------------------- #
def greedy_snake(image, points, alpha=1.0, beta=1.0, gamma=1.2, sigma=DEFAULT_SIGMA,
                 neighborhood=3, spacing=5.0, max_iterations=500, min_moved=2, curv_thresh=0.25):
    """
    Evolve a closed snake with the greedy algorithm.
    `points` = [(x, y), ...] initial contour (e.g. clicked by hand), `neighborhood` = odd search window.
    Returns (final_points as n x 2 float array, history = list of arrays, one per iteration).
    """
    if neighborhood < 3 or neighborhood % 2 == 0:
        raise ValueError("neighborhood must be an odd integer >= 3 (3, 5, 7, ...)")
    grad = np.hypot(*gradients(to_gray(image), sigma))
    h, w = grad.shape
    pts = resample_contour(points, spacing)
    n = len(pts)
    r = neighborhood // 2
    oy, ox = np.mgrid[-r:r + 1, -r:r + 1]
    offsets = np.stack([ox.ravel(), oy.ravel()], axis=1)            # (k, 2) as (dx, dy)
    grad_thresh = 0.4 * grad.max()
    betas = np.full(n, beta)
    history = [pts.copy()]

    for _ in range(max_iterations):
        d_avg = np.mean(np.hypot(*(np.roll(pts, -1, axis=0) - pts).T))
        moved = 0
        for i in range(n):
            prev, nxt = pts[i - 1], pts[(i + 1) % n]
            cand = np.rint(pts[i]) + offsets
            cand[:, 0] = np.clip(cand[:, 0], 0, w - 1)
            cand[:, 1] = np.clip(cand[:, 1], 0, h - 1)

            e_cont = (d_avg - np.hypot(*(cand - prev).T)) ** 2
            e_curv = np.sum((prev - 2 * cand + nxt) ** 2, axis=1)
            g = grad[cand[:, 1].astype(int), cand[:, 0].astype(int)]

            e_cont /= max(e_cont.max(), 1e-6)
            e_curv /= max(e_curv.max(), 1e-6)
            e_img = (g.min() - g) / max(g.max() - g.min(), 5.0)     # in [-1, 0]

            new = cand[np.argmin(alpha * e_cont + betas[i] * e_curv + gamma * e_img)]
            moved += bool(np.any(new != np.rint(pts[i])))
            pts[i] = new

        betas = np.where(_corner_points(pts, grad, curv_thresh, grad_thresh), 0.0, beta)
        history.append(pts.copy())
        if moved < min_moved:
            break
    return pts, history


# --------------------------------------------------------------------------- #
#  Chain code, perimeter, area
# --------------------------------------------------------------------------- #
def _segments(points, closed=True):
    """Consecutive point pairs as integer (x1, y1, x2, y2) - the format draw_shapes expects."""
    p = np.rint(np.asarray(points)).astype(int)
    nxt = np.roll(p, -1, axis=0) if closed else p[1:]
    return [(a[0], a[1], b[0], b[1]) for a, b in zip(p, nxt)]


def _pixel_path(points):
    """Closed 8-connected pixel path through the (rounded) contour points."""
    path = []
    for x1, y1, x2, y2 in _segments(points):
        k = max(abs(x2 - x1), abs(y2 - y1)) + 1
        x = np.rint(np.linspace(x1, x2, k)).astype(int)
        y = np.rint(np.linspace(y1, y2, k)).astype(int)
        path.extend(zip(x[:-1].tolist(), y[:-1].tolist()))
    out = path[:1]
    for q in path[1:]:
        if q != out[-1]:                                            # drop consecutive duplicates
            out.append(q)
    if len(out) > 1 and out[-1] == out[0]:
        out.pop()
    if len(out) < 2:
        raise ValueError("the contour collapsed to a single pixel - no chain code possible")
    return out


def chain_code(points):
    """
    8-direction Freeman chain code of the closed contour.
    Returns (start_xy, code): start pixel (x, y) and the codes 0..7 that walk around the contour
    and return to the start.
    """
    path = _pixel_path(points)
    code = [next(k for k in range(8) if (DX[k], DY[k]) == (b[0] - a[0], b[1] - a[1]))
            for a, b in zip(path, path[1:] + path[:1])]
    return path[0], code


def chain_perimeter(code):
    """Perimeter from a chain code: horizontal/vertical step = 1, diagonal step = sqrt(2)."""
    odd = int(np.sum(np.asarray(code) % 2 == 1))
    return float(len(code) - odd + odd * np.sqrt(2))


def chain_area(start_xy, code):
    """Area enclosed by the chain code: shoelace formula on the vertices the code visits."""
    code = np.asarray(code)
    x = start_xy[0] + np.r_[0, np.cumsum(DX[code])[:-1]]
    y = start_xy[1] + np.r_[0, np.cumsum(DY[code])[:-1]]
    return float(abs(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)) / 2.0)


# --------------------------------------------------------------------------- #
#  Drawing + manual initialisation
# --------------------------------------------------------------------------- #
def draw_snake(image, points, closed=True, thickness=1):
    """BGR copy of `image` with the contour drawn as green line segments (uses draw_shapes)."""
    if len(points) < 2:
        return draw_shapes(image)
    return draw_shapes(image, lines=_segments(points, closed), thickness=thickness)


def select_contour_by_hand(image, window="Draw the initial contour"):
    """
    Let the user click the initial contour around the object.
        left click  : add a point          right click / BACKSPACE : remove last point
        ENTER/SPACE : finish (needs >= 3)  ESC : cancel (returns [])
    """
    import cv2   # only for the window and the mouse - not for any processing
    pts = []

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            pts.append((x, y))
        elif event == cv2.EVENT_RBUTTONDOWN and pts:
            pts.pop()

    cv2.namedWindow(window)
    cv2.setMouseCallback(window, on_mouse)
    while True:
        cv2.imshow(window, draw_snake(image, pts, closed=len(pts) > 2))
        key = cv2.waitKey(20) & 0xFF
        if key in (13, 32) and len(pts) >= 3:
            break
        if key == 27:
            pts.clear()
            break
        if key == 8 and pts:
            pts.pop()
    cv2.destroyWindow(window)
    return list(pts)


# --------------------------------------------------------------------------- #
#  Command line (from CV_task2/):  python -m services.Active_contour image.png
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import argparse
    import cv2

    ap = argparse.ArgumentParser(description="Greedy snake with hand-drawn initial contour")
    ap.add_argument("image")
    ap.add_argument("--alpha", type=float, default=1.0)
    ap.add_argument("--beta", type=float, default=1.0)
    ap.add_argument("--gamma", type=float, default=1.2)
    ap.add_argument("--sigma", type=float, default=DEFAULT_SIGMA)
    ap.add_argument("--iterations", type=int, default=500)
    ap.add_argument("--out", default="snake_result.png")
    args = ap.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        raise SystemExit(f"cannot read {args.image}")
    init = select_contour_by_hand(img)
    if len(init) < 3:
        raise SystemExit("no contour drawn")

    final, hist = greedy_snake(img, init, alpha=args.alpha, beta=args.beta, gamma=args.gamma,
                               sigma=args.sigma, max_iterations=args.iterations)
    start, code = chain_code(final)
    print(f"iterations : {len(hist) - 1}")
    print(f"start pixel: {start}")
    print(f"chain code ({len(code)} steps):\n{''.join(map(str, code))}")
    print(f"perimeter  : {chain_perimeter(code):.2f} px")
    print(f"area       : {chain_area(start, code):.2f} px^2")

    result = draw_snake(img, final)
    cv2.imwrite(args.out, result)
    cv2.imshow("result", result)
    cv2.waitKey(0)