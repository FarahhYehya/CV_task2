"""
Part 1: Canny edges + lines / circles / ellipses, superimposed on the image.

One endpoint, because every detector uses the SAME Canny edge map: it is computed once and
passed to each detector.  detect_lines / detect_circles / detect_ellipses choose which detectors
run (ellipses are the slow one: ~3-10 s on 640x480).  All False -> only the Canny edge map.
"""
from fastapi import APIRouter, File, Form, UploadFile

from api.utils import read_image
from schemas.detection import Circle, Ellipse, Line, ShapesResponse
from services import Canny_and_objects_detection
from services.image_io import DEFAULT_SIGMA, encode_png

router = APIRouter(prefix="/api", tags=["Part 1 - edges and shapes"])


def to_models(model, rows):
    """Service tuples -> response models; tuple order = the model's field order."""
    return [model(**dict(zip(model.model_fields, row))) for row in rows]


@router.post("/shapes", response_model=ShapesResponse)
def shapes(
    image: UploadFile = File(...),
    # Canny
    low_threshold: float = Form(50, ge=0, description="Canny low threshold (gradient magnitude)"),
    high_threshold: float = Form(150, ge=0, description="Canny high threshold (gradient magnitude)"),
    sigma: float = Form(DEFAULT_SIGMA, ge=0, description="Gaussian blur strength (px), 0 = no blur"),
    # which detectors run
    detect_lines: bool = Form(True),
    detect_circles: bool = Form(True),
    detect_ellipses: bool = Form(True),
    # lines
    threshold: int = Form(60, ge=1, description="lines: min Hough votes (edge pixels on the line)"),
    min_line_length: int = Form(40, ge=1, description="lines: min segment length (px)"),
    max_line_gap: int = Form(10, ge=0, description="lines: max gap inside one segment (px)"),
    # circles
    min_radius: int = Form(10, ge=1, description="circles: min radius (px)"),
    max_radius: int | None = Form(None, ge=1, description="circles: max radius (px), empty = half the image"),
    min_votes: int = Form(30, ge=1, description="circles: min votes for a centre / a radius"),
    # ellipses
    min_axis_length: int = Form(10, ge=1, description="ellipses: min full minor axis (px)"),
    max_axis_length: int | None = Form(None, ge=1, description="ellipses: max full major axis (px), empty = image diagonal"),
    min_center_votes: int = Form(25, ge=1, description="ellipses: min votes for a centre"),
    # circles + ellipses
    min_edge_support: float = Form(0.8, ge=0, le=1, description="fraction of the outline that must lie on edges (0-1)"),
):
    img = read_image(image)
    edges = Canny_and_objects_detection.canny_edge_detector(img, low_threshold, high_threshold, sigma)

    lines = Canny_and_objects_detection.detect_lines(
        img, edges, threshold=threshold, min_line_length=min_line_length, max_line_gap=max_line_gap,
    ) if detect_lines else []
    circles = Canny_and_objects_detection.detect_circles(
        img, edges, sigma=sigma, min_radius=min_radius, max_radius=max_radius,
        min_votes=min_votes, min_edge_support=min_edge_support,
    ) if detect_circles else []
    ellipses = Canny_and_objects_detection.detect_ellipses(
        img, edges, sigma=sigma, min_axis_length=min_axis_length, max_axis_length=max_axis_length,
        min_center_votes=min_center_votes, min_edge_support=min_edge_support,
    ) if detect_ellipses else []

    return ShapesResponse(
        edges=encode_png(edges),
        image=encode_png(Canny_and_objects_detection.draw_shapes(img, lines, circles, ellipses)),
        lines=to_models(Line, lines),
        circles=to_models(Circle, circles),
        ellipses=to_models(Ellipse, ellipses),
    )
