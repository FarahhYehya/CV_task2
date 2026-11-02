"""
Response models of Part 1 (Canny + lines / circles / ellipses).
Field names are the same as the service tuples:  detect_lines -> (x1, y1, x2, y2),
detect_circles -> (cx, cy, r), detect_ellipses -> (cx, cy, width, height, angle).
All coordinates and lengths are in pixels (x to the right, y down).
"""
from pydantic import BaseModel, Field


class Line(BaseModel):
    x1: int = Field(description="start x (px)")
    y1: int = Field(description="start y (px)")
    x2: int = Field(description="end x (px)")
    y2: int = Field(description="end y (px)")


class Circle(BaseModel):
    cx: int = Field(description="centre x (px)")
    cy: int = Field(description="centre y (px)")
    r: int = Field(description="radius (px)")


class Ellipse(BaseModel):
    cx: int = Field(description="centre x (px)")
    cy: int = Field(description="centre y (px)")
    width: int = Field(description="full length of the major axis (px)")
    height: int = Field(description="full length of the minor axis (px)")
    angle: float = Field(description="angle of the major axis from the x-axis (degrees, 0-180)")


class ShapesResponse(BaseModel):
    edges: str = Field(description="Canny edge map as base64 PNG (white = edge)")
    image: str = Field(description="input image with the shapes drawn on it, base64 PNG "
                                   "(lines green, circles red, ellipses blue)")
    lines: list[Line]
    circles: list[Circle]
    ellipses: list[Ellipse]
