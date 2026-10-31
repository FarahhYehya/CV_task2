"""
Shape detection implemented from scratch (NumPy only - no OpenCV inside).

Main functions  (all blur-based ones take `sigma=` - the Gaussian blur strength, default 1.4)
--------------
canny_edge_detector(image)           -> binary edge image (0 / 255)
detect_lines(image, edges)           -> [(x1, y1, x2, y2), ...]            Hough (rho, theta)
detect_circles(image, edges)         -> [(cx, cy, r), ...]                 gradient Hough (a, b) + radius histogram
detect_ellipses(image, edges)        -> [(cx, cy, width, height, angle)]   reduced-parameter Hough
draw_shapes(image, lines, circles, ellipses) -> image with the shapes drawn on it

Ellipse method (5 parameters reduced to 2 + 3 small ones, following the idea of
Xie & Ji, "A new efficient ellipse detection method", 2002; Tsuji & Matsumoto 1978):
  1. Every ellipse is centrally symmetric, so two edge points whose gradients are
     opposite (anti-parallel tangents) have the ellipse centre as their midpoint.
     These midpoints vote in a 2-D accumulator -> candidate centres (x0, y0).
  2. For each candidate centre only the edge points that have a mirror edge point
     on the other side (2*c - p) are kept.  With the centre known, the ellipse has
     only 3 unknowns (a, b, phi): a 3-D accumulator over (a, b, phi) is filled and
     its peak gives the ellipse.  A least-squares refinement then sharpens it.
  3. The ellipse is accepted only if its outline lies on detected edges.

Coordinates are image coordinates (x to the right, y down).  An ellipse is returned
as (cx, cy, width, height, angle): `width` is the full length of the axis that makes
`angle` degrees with the x-axis, `height` the full length of the other axis.
"""
import numpy as np


DEFAULT_SIGMA = 1.4      # Gaussian blur strength used everywhere (change it per call with `sigma=`)


# --------------------------------------------------------------------------- #
#  Shared helpers (each piece of logic lives in exactly one place)
# --------------------------------------------------------------------------- #
def _to_gray(image):
    """Accept grayscale, BGR or BGRA (any dtype) and return float32 gray in 0..255."""
    if image is None:
        raise ValueError("image is empty")
    image = np.asarray(image)
    if image.size == 0:
        raise ValueError("image is empty")
    image = image.astype(np.float32)
    if image.dtype != np.uint8 and (image.max() > 255 or image.min() < 0 or image.max() <= 1.0):
        lo, hi = float(image.min()), float(image.max())
        image = (image - lo) * (255.0 / (hi - lo)) if hi > lo else np.zeros_like(image)

    if image.ndim == 2:
        return image
    if image.ndim == 3 and image.shape[2] == 1:
        return image[:, :, 0]
    if image.ndim == 3 and image.shape[2] in (3, 4):          # BGR / BGRA
        return 0.114 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.299 * image[:, :, 2]
    raise ValueError("image must be grayscale, BGR or BGRA")


def _sliding(arr, radius, axis, op=np.add, weights=None, mode="constant"):
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


def _window_op(arr, radius, op, axes=None):
    """Separable (2r+1) window filter (sum / max / or) over `axes` (default: all axes)."""
    for axis in (range(arr.ndim) if axes is None else axes):
        arr = _sliding(arr, radius, axis, op)
    return arr


def _gaussian_blur(gray, sigma=DEFAULT_SIGMA):
    """Separable Gaussian blur.  sigma <= 0 means 'no blur'."""
    gray = np.asarray(gray, dtype=np.float32)
    if sigma <= 0:
        return gray
    r = max(1, int(round(3 * sigma)))
    x = np.arange(-r, r + 1, dtype=np.float32)
    kernel = np.exp(-(x ** 2) / (2 * sigma ** 2))
    kernel /= kernel.sum()
    blurred = _sliding(gray, r, 0, weights=kernel, mode="edge")
    return _sliding(blurred, r, 1, weights=kernel, mode="edge")


def _gradients(gray, sigma=DEFAULT_SIGMA):
    """Gaussian blur followed by 3x3 Sobel.  Returns (gx, gy)."""
    p = np.pad(_gaussian_blur(gray, sigma), 1, mode="edge")
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[1:-1, :-2] + p[2:, :-2])
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]) - (p[:-2, :-2] + 2 * p[:-2, 1:-1] + p[:-2, 2:])
    return gx, gy


def _edge_points(image, edge_image, sigma):
    """
    Shared set-up of the circle and ellipse detectors.
    Returns (edge_mask, xs, ys, dx, dy): the boolean edge map, the coordinates of
    the edge pixels and the unit gradient direction (dx, dy) at each of them.
    """
    gray = _to_gray(image)
    edges = edge_image if edge_image is not None else canny_edge_detector(image, sigma=sigma)
    gx, gy = _gradients(gray, sigma)
    ys, xs = np.nonzero(edges)
    mag = np.hypot(gx[ys, xs], gy[ys, xs])
    good = mag > 1e-6
    xs, ys, mag = xs[good], ys[good], mag[good]
    return np.ascontiguousarray(edges > 0), xs, ys, gx[ys, xs] / mag, gy[ys, xs] / mag


def _near_edge(edge_mask, tolerance):
    """Boolean map: True within +/- `tolerance` pixels of an edge."""
    return _window_op(edge_mask, tolerance, np.logical_or)


def _local_maxima(acc, radius, min_votes):
    """Boolean mask of accumulator cells that are the maximum of their window and >= min_votes."""
    return (acc == _window_op(acc, radius, np.maximum)) & (acc >= min_votes)


def _pick_peaks(acc, min_votes, radius, min_separation, max_peaks):
    """Strongest local maxima of a 2-D accumulator, at least `min_separation` px apart -> [(x, y)]."""
    py, px = np.nonzero(_local_maxima(acc, radius, min_votes))
    chosen = []
    for k in np.argsort(-acc[py, px]):
        if all(np.hypot(px[k] - a, py[k] - b) >= min_separation for a, b in chosen):
            chosen.append((int(px[k]), int(py[k])))
        if len(chosen) >= max_peaks:
            break
    return chosen


def _in_bounds(x, y, h, w):
    """Boolean mask: which integer coordinates (x, y) lie inside an h x w image."""
    return (x >= 0) & (x < w) & (y >= 0) & (y < h)


def _rotate(px, py, theta):
    """Coordinates of (px, py) in a frame rotated by `theta` radians (axis 1 along theta)."""
    c, s = np.cos(theta), np.sin(theta)
    return px * c + py * s, -px * s + py * c


def _ellipse_points(cx, cy, a, b, phi_deg, n):
    """n points on the outline of an ellipse (a, b = semi-axes; a circle is a == b)."""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    c, s = np.cos(np.deg2rad(phi_deg)), np.sin(np.deg2rad(phi_deg))
    ex, ey = a * np.cos(t), b * np.sin(t)
    return cx + ex * c - ey * s, cy + ex * s + ey * c


def _ellipse_error(px, py, a, b, phi_deg):
    """|normalised radius - 1| of every point: 0 = exactly on the ellipse."""
    u, v = _rotate(px, py, np.deg2rad(phi_deg))
    return np.abs(np.hypot(u / a, v / b) - 1)


def _outline_support(near_edge, cx, cy, a, b, phi_deg, min_inside):
    """
    Fraction of a circle / ellipse outline lying on edge pixels.
    Returns None if less than `min_inside` of the outline is inside the image.
    """
    h, w = near_edge.shape
    n = max(72, int(np.pi * (3 * (a + b) - np.sqrt((3 * a + b) * (a + 3 * b)))))
    ox, oy = _ellipse_points(cx, cy, a, b, phi_deg, n)
    ox, oy = np.rint(ox).astype(int), np.rint(oy).astype(int)
    inside = _in_bounds(ox, oy, h, w)
    if inside.mean() < min_inside:
        return None
    return float(near_edge[oy[inside], ox[inside]].mean())


def _remove_duplicates(found):
    """
    found = [(support, cx, cy, width, height, angle)].  Keeps the best-supported shape of every
    group with the same centre and similar axes (e.g. inner + outer edge of a thick stroke).
    """
    kept = []
    for _, cx, cy, wd, ht, ang in sorted(found, key=lambda f: -f[0]):
        tol = max(0.1 * max(wd, ht), 13.0)   # > 2 x stroke thickness
        if not any(np.hypot(cx - kx, cy - ky) <= max(0.15 * max(wd, ht), 5.0) and
                   ((abs(wd - kw) < tol and abs(ht - kh) < tol) or
                    (abs(wd - kh) < tol and abs(ht - kw) < tol))
                   for kx, ky, kw, kh, _ in kept):
            kept.append((cx, cy, wd, ht, ang))
    return kept


# --------------------------------------------------------------------------- #
#  Canny edge detector
# --------------------------------------------------------------------------- #
def _hysteresis(strong, weak):
    """Keep every weak pixel that is 8-connected (through weak pixels) to a strong one."""
    h, w = strong.shape
    W = w + 2
    visited = np.zeros((h + 2) * W, dtype=bool)
    candidate = np.pad(weak, 1).reshape(-1)
    frontier = np.flatnonzero(np.pad(strong, 1).reshape(-1))
    visited[frontier] = True
    offsets = np.array([-W - 1, -W, -W + 1, -1, 1, W - 1, W, W + 1])
    while frontier.size:
        nb = (frontier[:, None] + offsets).ravel()
        nb = nb[candidate[nb] & ~visited[nb]]
        nb = np.unique(nb)
        visited[nb] = True
        frontier = nb
    return visited.reshape(h + 2, W)[1:-1, 1:-1]


def canny_edge_detector(image, low_threshold=50, high_threshold=150, sigma=DEFAULT_SIGMA):
    """Canny edge detector.  `sigma` = Gaussian blur strength.  Returns uint8: edges = 255, else 0."""
    if low_threshold > high_threshold:
        low_threshold, high_threshold = high_threshold, low_threshold

    h, w = _to_gray(image).shape

    # 1-2) Gaussian smoothing + Sobel gradients
    gx, gy = _gradients(_to_gray(image), sigma)
    magnitude = np.hypot(gx, gy)
    angle = (np.rad2deg(np.arctan2(gy, gx)) + 180) % 180

    # 3) Non-maximum suppression: compare with the two neighbours along the gradient direction
    #    (angle quantised to 0, 45, 90, 135 degrees -> neighbour offset step_x, step_y)
    q = ((angle + 22.5) // 45).astype(int) % 4
    step_y, step_x = np.array([0, 1, 1, 1])[q], np.array([1, 1, 0, -1])[q]
    padded = np.pad(magnitude, 1, mode="constant")
    yy, xx = np.indices((h, w))
    before = padded[yy + 1 - step_y, xx + 1 - step_x]
    after = padded[yy + 1 + step_y, xx + 1 + step_x]
    nms = np.where((magnitude >= before) & (magnitude > after), magnitude, 0)
    nms[[0, -1], :] = 0
    nms[:, [0, -1]] = 0

    # 4-5) Double threshold + hysteresis
    strong = nms >= high_threshold
    weak = nms >= low_threshold
    return _hysteresis(strong, weak).astype(np.uint8) * 255


# --------------------------------------------------------------------------- #
#  Hough transform for lines
# --------------------------------------------------------------------------- #
def _merge_similar_lines(lines, angle_tol_deg=5.0, dist_tol=10.0, gap_tol=25.0):
    """Drop duplicate segments (both sides of a thick stroke) and join collinear pieces."""
    def length(s):
        return np.hypot(s[2] - s[0], s[3] - s[1])

    def direction(s):
        return np.arctan2(s[3] - s[1], s[2] - s[0])

    def try_merge(base, other):
        """Merge `other` into `base` if they are parallel, on the same line and close together."""
        theta, base_len = direction(base), length(base)
        d_ang = np.degrees(abs(theta - direction(other))) % 180
        if base_len < 1e-6 or min(d_ang, 180 - d_ang) > angle_tol_deg:
            return None
        # ends of `other` in the frame of `base`: t = along the line, d = distance from it
        t, d = _rotate(np.array([other[0], other[2]]) - base[0], np.array([other[1], other[3]]) - base[1], theta)
        if np.abs(d).max() > dist_tol or max(t.min() - base_len, -t.max(), 0) > gap_tol:
            return None
        t0, t1 = min(0.0, t.min()), max(base_len, t.max())
        c, s = np.cos(theta), np.sin(theta)
        return np.array([base[0] + c * t0, base[1] + s * t0, base[0] + c * t1, base[1] + s * t1])

    segs = sorted((np.array(l, dtype=np.float64) for l in lines), key=lambda s: -length(s))
    merged = True
    while merged:
        merged, out = False, []
        for s in segs:
            for i, k in enumerate(out):
                m = try_merge(k, s)
                if m is not None:
                    out[i], merged = m, True
                    break
            else:
                out.append(s)
        segs = sorted(out, key=lambda s: -length(s))
    return [tuple(int(round(v)) for v in s) for s in segs]


def detect_lines(image, edge_image=None, rho=1, theta=np.pi / 180,
                 threshold=60, min_line_length=40, max_line_gap=10,
                 max_distance=2.0):
    """
    Hough transform for lines:  rho = x*cos(theta) + y*sin(theta).
    1. every edge pixel votes for all (rho, theta) cells it could lie on;
    2. local maxima of the accumulator with >= `threshold` votes are lines;
    3. for each line the edge pixels within `max_distance` of it are projected onto
       the line, split at gaps > `max_line_gap` and kept if >= `min_line_length` long.
    Returns [(x1, y1, x2, y2), ...].
    """
    edges = edge_image if edge_image is not None else canny_edge_detector(image)
    ys, xs = np.nonzero(edges)
    if len(xs) == 0:
        return []
    h, w = edges.shape

    thetas = np.arange(0, np.pi, theta)
    cos_t, sin_t = np.cos(thetas), np.sin(thetas)
    max_rho = int(np.ceil(np.hypot(h, w) / rho))
    n_rho = 2 * max_rho + 1
    xs, ys = xs.astype(np.float64), ys.astype(np.float64)

    # 1) voting (chunked so memory stays small)
    acc = np.zeros(len(thetas) * n_rho, dtype=np.int64)
    theta_offset = (np.arange(len(thetas)) * n_rho)[None, :]
    chunk = max(1, 2_000_000 // len(thetas))
    for s in range(0, len(xs), chunk):
        r = np.rint((xs[s:s + chunk, None] * cos_t + ys[s:s + chunk, None] * sin_t) / rho).astype(np.int64)
        acc += np.bincount((r + max_rho + theta_offset).ravel(), minlength=acc.size)
    acc = acc.reshape(len(thetas), n_rho)

    # 2) peaks (accumulator lightly smoothed along rho, then local maxima)
    ti, ri = np.nonzero(_local_maxima(acc, 2, threshold))
    order = np.argsort(-acc[ti, ri])[:150]

    # 3) turn each peak into segments
    segments = []
    for k in order:
        th, rh = thetas[ti[k]], (ri[k] - max_rho) * rho
        sel = np.abs(_rotate(xs, ys, th)[0] - rh) <= max_distance + 1
        for _ in range(2):          # re-fit the line to its own pixels (undoes the angle quantisation)
            if sel.sum() < min_line_length:
                break
            mx, my = xs[sel].mean(), ys[sel].mean()
            _, vecs = np.linalg.eigh(np.cov(np.stack([xs[sel] - mx, ys[sel] - my])))
            th = np.arctan2(vecs[1, 1], vecs[0, 1])                 # direction of the line
            sel = np.abs(_rotate(xs - mx, ys - my, th)[1]) <= max_distance
        if sel.sum() < min_line_length:
            continue
        t, d = _rotate(xs[sel] - mx, ys[sel] - my, th)               # along / across the line
        px, py = xs[sel], ys[sel]
        srt = np.argsort(t)
        t, d, px, py = t[srt], d[srt], px[srt], py[srt]
        breaks = np.flatnonzero(np.diff(t) > max_line_gap) + 1
        for a, b in zip(np.r_[0, breaks], np.r_[breaks, len(t)]):
            if t[b - 1] - t[a] < min_line_length or (b - a) < 0.6 * min_line_length:
                continue
            # straightness: an arc of a big circle also fits inside the distance band
            lo, hi = np.percentile(d[a:b], [5, 95])
            if hi - lo <= max_distance:
                segments.append((int(px[a]), int(py[a]), int(px[b - 1]), int(py[b - 1])))

    return _merge_similar_lines(segments)


# --------------------------------------------------------------------------- #
#  Hough transform for circles
# --------------------------------------------------------------------------- #
def detect_circles(image, edge_image=None, sigma=DEFAULT_SIGMA, min_radius=10, max_radius=None,
                   min_votes=30, min_edge_support=0.8, max_candidates=40):
    """
    Gradient-based Hough transform for circles.
    1. Every edge pixel votes for the centres lying on its gradient line
       (p +/- r * gradient_direction for every radius r) in a 2-D (a, b) accumulator.
    2. Peaks of that accumulator are candidate centres.
    3. For every centre a histogram of the distances to the edge pixels gives the
       radius (several radii per centre are possible -> concentric circles).
    4. A circle is kept only if >= `min_edge_support` of its outline lies on edges.
    `sigma` = Gaussian blur strength used for the gradients (and for Canny if no edge_image).
    Returns [(cx, cy, r), ...].
    """
    edge_mask, xs, ys, dx, dy = _edge_points(image, edge_image, sigma)
    h, w = edge_mask.shape
    if max_radius is None:
        max_radius = min(h, w) // 2
    if max_radius < min_radius or len(xs) < min_votes:
        return []

    # 1) voting for centres
    radii = np.arange(min_radius, max_radius + 1, dtype=np.float32)
    acc = np.zeros(h * w, dtype=np.int64)
    chunk = max(1, 1_000_000 // len(radii))
    for s in range(0, len(xs), chunk):
        for sign in (1.0, -1.0):
            cx = np.rint(xs[s:s + chunk, None] + sign * dx[s:s + chunk, None] * radii).astype(np.int64)
            cy = np.rint(ys[s:s + chunk, None] + sign * dy[s:s + chunk, None] * radii).astype(np.int64)
            ok = _in_bounds(cx, cy, h, w)
            acc += np.bincount((cy * w + cx)[ok], minlength=acc.size)

    # 2) candidate centres
    centres = _pick_peaks(_window_op(acc.reshape(h, w), 1, np.add), min_votes,
                          radius=4, min_separation=5, max_peaks=max_candidates)
    near_edge = _near_edge(edge_mask, 2)

    # 3) radius histogram for every centre + 4) edge-support check
    found = []
    for cx, cy in centres:
        rx, ry = xs - cx, ys - cy
        dist = np.hypot(rx, ry)
        radial = np.abs(dx * rx + dy * ry) / np.maximum(dist, 1e-6)       # gradient must point to/from the centre
        sel = (radial > 0.9) & (dist >= min_radius) & (dist <= max_radius)
        if sel.sum() < min_votes:
            continue
        hist = np.bincount(np.rint(dist[sel]).astype(int), minlength=max_radius + 3).astype(np.int64)
        for r0 in np.flatnonzero(_local_maxima(_window_op(hist, 1, np.add), 3, min_votes)):
            if r0 < min_radius:
                continue
            r = float(dist[sel & (np.abs(dist - r0) <= 2)].mean())
            support = _outline_support(near_edge, cx, cy, r, r, 0.0, min_inside=0.25)
            if support is not None and support >= min_edge_support:
                found.append((support, cx, cy, 2 * r, 2 * r, 0.0))       # a circle is an ellipse with a == b

    return [(int(cx), int(cy), int(round(wd / 2))) for cx, cy, wd, _, _ in _remove_duplicates(found)]


# --------------------------------------------------------------------------- #
#  Hough transform for ellipses (reduced parameters)
# --------------------------------------------------------------------------- #
def _centre_candidates(xs, ys, ang, h, w, min_pair_dist, max_pair_dist,
                       min_votes, max_candidates, n_bins=72, seed=0):
    """Stage 1: midpoints of edge-point pairs with anti-parallel gradients vote for the centre."""
    rng = np.random.default_rng(seed)
    if len(xs) > 5000:                                    # keep the pair count manageable
        pick = rng.choice(len(xs), 5000, replace=False)
        xs, ys, ang = xs[pick], ys[pick], ang[pick]
    bins = np.floor((ang + np.pi) / (2 * np.pi) * n_bins).astype(int) % n_bins
    members = [np.flatnonzero(bins == k) for k in range(n_bins)]

    acc = np.zeros(h * w, dtype=np.int64)
    for k in range(n_bins):
        ax, ay = xs[members[k]][:, None], ys[members[k]][:, None]
        for dk in (-1, 0, 1):                              # opposite bin (+/- 1 for angle noise)
            opp = members[(k + n_bins // 2 + dk) % n_bins]
            bx, by = xs[opp][None, :], ys[opp][None, :]
            d2 = (ax - bx) ** 2 + (ay - by) ** 2
            ok = (d2 >= min_pair_dist ** 2) & (d2 <= max_pair_dist ** 2)
            mid = (((ay + by) // 2) * w + (ax + bx) // 2)[ok]
            if mid.size:
                acc += np.bincount(mid, minlength=acc.size)

    return _pick_peaks(_window_op(acc.reshape(h, w), 1, np.add), min_votes,
                       radius=3, min_separation=4, max_peaks=max_candidates)


def _axes_peak(px, py, a_min, a_max, angle_step):
    """Stage 2: 3-D accumulator over (phi, a, b) for points relative to a known centre."""
    phis = np.deg2rad(np.arange(0, 180, angle_step))
    a_vals = np.arange(a_min, a_max + 1, dtype=np.float32)
    n_a, n_b = len(a_vals), a_max + 1
    acc = np.zeros((len(phis), n_a, n_b), dtype=np.int32)
    a_index = (np.arange(n_a) * n_b)[None, :]
    for ip, phi in enumerate(phis):
        u, v = _rotate(px, py, phi)
        ratio = u[:, None] / a_vals[None, :]
        valid = np.abs(ratio) < 0.98
        b = np.rint(np.abs(v)[:, None] / np.sqrt(np.clip(1 - ratio ** 2, 1e-6, None))).astype(np.int64)
        valid &= (b >= a_min) & (b <= a_vals[None, :])
        acc[ip] = np.bincount((a_index + b)[valid], minlength=n_a * n_b).reshape(n_a, n_b)

    acc = _window_op(acc, 1, np.add, axes=(1, 2))               # smooth a and b
    acc = acc + np.roll(acc, 1, axis=0) + np.roll(acc, -1, axis=0)   # smooth phi (wraps at 180 deg)
    ip, ia, ib = np.unravel_index(np.argmax(acc), acc.shape)
    return float(a_vals[ia]), float(ib), float(np.rad2deg(phis[ip])), int(acc[ip, ia, ib])


def _refine_ellipse(px, py, a, b, phi_deg):
    """Least-squares refit of x^T M x = 1 (centred conic) on the points that agree with (a, b, phi)."""
    inl = _ellipse_error(px, py, a, b, phi_deg) < 0.12
    if inl.sum() < 8:
        return a, b, phi_deg
    x, y = px[inl], py[inl]
    coef, *_ = np.linalg.lstsq(np.stack([x * x, x * y, y * y], 1), np.ones(len(x)), rcond=None)
    M = np.array([[coef[0], coef[1] / 2], [coef[1] / 2, coef[2]]])
    vals, vecs = np.linalg.eigh(M)
    if vals[0] <= 1e-9:
        return a, b, phi_deg
    ra, rb = 1 / np.sqrt(vals[0]), 1 / np.sqrt(vals[1])          # a >= b
    return float(ra), float(rb), float(np.rad2deg(np.arctan2(vecs[1, 0], vecs[0, 0])) % 180)


def _remove_circles(ellipses, circle_ratio=0.9):
    """Drop near-circular ellipses: those whose short axis is >= circle_ratio x their long axis."""
    return [e for e in ellipses if min(e[2], e[3]) < circle_ratio * max(e[2], e[3])]


def detect_ellipses(image, edge_image=None, sigma=DEFAULT_SIGMA, min_axis_length=10,
                    max_axis_length=None, min_center_votes=25, min_edge_support=0.8,
                    min_aspect=0.2, max_candidates=40, angle_step=5):
    """
    Reduced-parameter Hough transform for ellipses (see the module docstring).
    `sigma` = Gaussian blur strength used for the gradients (and for Canny if no edge_image).
    Near-circular results (short axis >= 90% of the long axis) are left out: those are reported by
    detect_circles, so every shape is counted once.
    Returns [(cx, cy, width, height, angle_degrees), ...].
    """
    edge_mask, xs, ys, dx, dy = _edge_points(image, edge_image, sigma)
    h, w = edge_mask.shape
    if max_axis_length is None:
        max_axis_length = int(np.hypot(h, w))
    if len(xs) < 20:
        return []

    near1 = _near_edge(edge_mask, 1)      # +/- 1 px  (mirror-point test)
    near2 = _near_edge(edge_mask, 2)      # +/- 2 px  (outline support)

    # Stage 1: centre candidates from anti-parallel point pairs
    centres = _centre_candidates(xs, ys, np.arctan2(dy, dx), h, w, min_pair_dist=min_axis_length,
                                 max_pair_dist=max_axis_length, min_votes=min_center_votes,
                                 max_candidates=max_candidates)

    # Stage 2: (a, b, phi) for every centre
    a_min = max(3, int(min_axis_length // 2))
    found = []
    for cx, cy in centres:
        mx, my = 2 * cx - xs, 2 * cy - ys                        # mirror image of every edge point
        inside = _in_bounds(mx, my, h, w)
        sym = np.zeros(len(xs), dtype=bool)
        sym[inside] = near1[my[inside], mx[inside]]
        px, py = (xs[sym] - cx).astype(np.float32), (ys[sym] - cy).astype(np.float32)
        keep = np.hypot(px, py) <= max_axis_length / 2
        px, py = px[keep], py[keep]

        for _ in range(4):                                        # several ellipses may share a centre
            if len(px) < 12:
                break
            a_max = int(min(max_axis_length / 2, np.ceil(np.hypot(px, py).max())))
            if a_max < a_min:
                break
            a, b, phi, votes = _axes_peak(px, py, a_min, a_max, angle_step)
            if votes < 12:
                break
            a, b, phi = _refine_ellipse(px, py, a, b, phi)
            if 2 * b < min_axis_length or 2 * a > max_axis_length or b < min_aspect * a:
                break   # too small / too big / a flat sliver (a straight edge, not an ellipse)
            support = _outline_support(near2, cx, cy, a, b, phi, min_inside=0.9)
            if support is None or support < min_edge_support:
                break
            found.append((support, cx, cy, 2 * a, 2 * b, phi))
            rest = _ellipse_error(px, py, a, b, phi) > 0.15      # remove this ellipse's points
            px, py = px[rest], py[rest]

    result = [(int(cx), int(cy), int(round(wd)), int(round(ht)), float(ang))
              for cx, cy, wd, ht, ang in _remove_duplicates(found)]
    return _remove_circles(result)


# --------------------------------------------------------------------------- #
#  Superimpose the detected shapes on the image
# --------------------------------------------------------------------------- #
def draw_shapes(image, lines=(), circles=(), ellipses=(), thickness=2):
    """
    Return a BGR copy of `image` with the shapes drawn on it:
    lines = green, circles = red, ellipses = blue (BGR colours).
    """
    img = np.asarray(image)
    if img.ndim == 2:
        img = np.stack([img] * 3, axis=2)
    out = img[:, :, :3].astype(np.uint8).copy()
    h, w = out.shape[:2]
    r = thickness // 2

    def plot(x, y, colour):
        x, y = np.rint(x).astype(int), np.rint(y).astype(int)
        for oy in range(-r, r + 1):
            for ox in range(-r, r + 1):
                xx, yy = x + ox, y + oy
                ok = _in_bounds(xx, yy, h, w)
                out[yy[ok], xx[ok]] = colour

    for x1, y1, x2, y2 in lines:
        n = int(max(abs(x2 - x1), abs(y2 - y1))) + 1
        plot(np.linspace(x1, x2, n), np.linspace(y1, y2, n), (0, 255, 0))
    for cx, cy, rad in circles:
        plot(*_ellipse_points(cx, cy, rad, rad, 0, 720), (0, 0, 255))
        plot(np.array([cx]), np.array([cy]), (0, 0, 255))
    for cx, cy, wd, ht, angle in ellipses:
        plot(*_ellipse_points(cx, cy, wd / 2.0, ht / 2.0, angle, 720), (255, 0, 0))
    return out
