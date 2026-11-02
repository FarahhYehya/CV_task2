"""
Part 2: greedy snake from a hand-drawn initial contour -> chain code, perimeter, area.

The initial contour is clicked in the browser and sent as the `points` form field
(JSON list of [x, y] pairs in image pixels).  Draw it AROUND the object: the snake shrinks.
"""
from fastapi import APIRouter, File, Form, UploadFile
from pydantic import ValidationError

from api.utils import read_image
from schemas.snake import POINTS, SnakeResponse
from services.Active_contour import chain_area, chain_code, chain_perimeter, draw_snake, greedy_snake
from services.image_io import DEFAULT_SIGMA, encode_png

router = APIRouter(prefix="/api", tags=["Part 2 - active contour"])


def parse_points(text):
    """'[[x, y], ...]' -> list of (x, y).  A malformed list becomes a ValueError -> HTTP 400."""
    try:
        return POINTS.validate_json(text)
    except ValidationError:
        raise ValueError('points must be a JSON list of [x, y] pairs, e.g. [[40, 40], [200, 40], [200, 200]]')


@router.post("/snake", response_model=SnakeResponse)
def snake(
    image: UploadFile = File(...),
    points: str = Form(..., description="initial contour: JSON list of [x, y] pairs (px), at least 3"),
    alpha: float = Form(1.0, ge=0, description="continuity weight (even spacing)"),
    beta: float = Form(1.0, ge=0, description="curvature weight (smoothness)"),
    gamma: float = Form(1.2, ge=0, description="image weight (pull to edges)"),
    sigma: float = Form(DEFAULT_SIGMA, ge=0, description="Gaussian blur before the gradient (px)"),
    neighborhood: int = Form(3, description="odd search window side (px): 3, 5, 7, ..."),
    spacing: float = Form(5.0, gt=0, description="distance between contour points (px)"),
    max_iterations: int = Form(500, ge=1, description="stop after this many iterations"),
    min_moved: int = Form(2, ge=0, description="stop when fewer points than this moved in one iteration"),
    curv_thresh: float = Form(0.25, ge=0, description="curvature above which a point on an edge is a corner (beta = 0)"),
):
    img = read_image(image)
    final, history = greedy_snake(img, parse_points(points), alpha=alpha, beta=beta, gamma=gamma, sigma=sigma,
                                  neighborhood=neighborhood, spacing=spacing, max_iterations=max_iterations,
                                  min_moved=min_moved, curv_thresh=curv_thresh)
    start, code = chain_code(final)
    return SnakeResponse(
        image=encode_png(draw_snake(img, final)),
        points=final.tolist(),
        history=[h.tolist() for h in history],
        chain_start=start,
        chain_code=code,
        perimeter=chain_perimeter(code),
        area=chain_area(start, code),
    )
