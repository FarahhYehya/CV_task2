"""Helpers shared by the routers."""
from fastapi import UploadFile

from services.image_io import decode_image


def read_image(upload: UploadFile):
    """Uploaded file -> BGR uint8 array, the input type of every service."""
    return decode_image(upload.file.read(), upload.filename or "uploaded file")
