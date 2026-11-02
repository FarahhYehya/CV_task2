"""
REST API for the services (one router per part of the assignment).

Run from CV_task2/:
    uvicorn api.main:app --reload
Docs (try every endpoint in the browser): http://127.0.0.1:8000/docs

Input : multipart form. The image is uploaded as a file, options are form fields
        with the same names and defaults as the service functions.
Output: JSON, shaped by the models in schemas/. Every image is a base64-encoded PNG string.
Errors: invalid option, image or contour (ValueError in a service) -> 400 {"detail": "..."}.
        Wrong type / out-of-range value checked by FastAPI -> 422.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from api.routers import detection, snake

app = FastAPI(title="CV_task2 API", version="1.0.0")


@app.exception_handler(ValueError)
def value_error_handler(request, exc):
    """Every ValueError raised by a service (bad option, image or contour) becomes HTTP 400."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(detection.router)
app.include_router(snake.router)
