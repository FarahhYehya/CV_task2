"""
Request / response models of Part 2 (greedy snake + chain code).
A point is (x, y) in pixels (x to the right, y down).
"""
from pydantic import BaseModel, Field, TypeAdapter

Point = tuple[float, float]

# parses the `points` form field: a JSON list of [x, y] pairs, e.g. "[[40, 40], [200, 40], [200, 200]]"
POINTS = TypeAdapter(list[Point])


class SnakeResponse(BaseModel):
    image: str = Field(description="input image with the final contour drawn on it, base64 PNG")
    points: list[Point] = Field(description="final contour points (px)")
    history: list[list[Point]] = Field(description="contour after every iteration; [0] = initial "
                                                   "(resampled) contour, last = final contour")
    chain_start: tuple[int, int] = Field(description="start pixel (x, y) of the chain code")
    chain_code: list[int] = Field(description="Freeman 8-direction codes 0-7 (0 = right, 2 = up, "
                                              "4 = left, 6 = down)")
    perimeter: float = Field(description="perimeter from the chain code (px): straight step 1, diagonal sqrt(2)")
    area: float = Field(description="area inside the contour (px^2), shoelace formula on the chain-code vertices")
