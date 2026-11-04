import io
from pathlib import Path
from typing import BinaryIO

import fitz
from fastapi import HTTPException
from PIL import Image

WATERMARK_MARGIN = 36
DIAGONAL_SCALE = 1.25


def rotate_pdf(
    file: BinaryIO,
    output_path: Path,
    angle: int,
    pages: list[int] | None = None,
) -> None:
    """angle is assumed pre-validated (90/180/270) by the router boundary."""
    doc = fitz.open(stream=file.read(), filetype="pdf")
    total = len(doc)
    targets = pages if pages else list(range(1, total + 1))
    for page_num in targets:
        if 1 <= page_num <= total:
            page = doc[page_num - 1]
            page.set_rotation(page.rotation + angle)
    doc.save(str(output_path))
    doc.close()


def rotate_pdf_map(
    file: BinaryIO,
    output_path: Path,
    rotations: dict[int, int],
) -> None:
    for angle in rotations.values():
        if angle % 90 != 0:
            raise HTTPException(
                status_code=400, detail="Angle must be a multiple of 90."
            )

    doc = fitz.open(stream=file.read(), filetype="pdf")
    total = len(doc)
    for page_num, angle in rotations.items():
        if 1 <= page_num <= total:
            page = doc[page_num - 1]
            page.set_rotation(angle % 360)
    doc.save(str(output_path))
    doc.close()


def _fit_font_size(text: str, avail_width: float, fontname: str = "helv") -> float:
    unit_width = fitz.get_text_length(text, fontname=fontname, fontsize=1)
    if unit_width <= 0:
        return 12
    return max(6.0, min(avail_width / unit_width, 400.0))


def add_text_watermark(
    file: BinaryIO,
    output_path: Path,
    text: str,
    position: str,
    opacity: float,
    pages: list[int] | None = None,
) -> None:
    doc = fitz.open(stream=file.read(), filetype="pdf")
    total = len(doc)
    targets = pages if pages else list(range(1, total + 1))
    color = (0.5, 0.5, 0.5)
    fontname = "helv"

    for page_num in targets:
        if page_num < 1 or page_num > total:
            continue
        page = doc[page_num - 1]
        rect = page.rect
        avail_width = rect.width - 2 * WATERMARK_MARGIN
        if position == "diagonal":
            avail_width *= DIAGONAL_SCALE
        font_size = _fit_font_size(text, avail_width, fontname)
        text_width = fitz.get_text_length(text, fontname=fontname, fontsize=font_size)
        x = rect.x0 + (rect.width - text_width) / 2
        y = _text_baseline_y(rect, position, font_size)

        if position == "diagonal":
            center = fitz.Point(rect.x0 + rect.width / 2, rect.y0 + rect.height / 2)
            shape = page.new_shape()
            shape.insert_text(
                fitz.Point(x, y),
                text,
                fontname=fontname,
                fontsize=font_size,
                color=color,
                stroke_opacity=opacity,
                fill_opacity=opacity,
                morph=(center, fitz.Matrix(45)),
            )
            shape.commit(overlay=True)
        else:
            page.insert_text(
                (x, y),
                text,
                fontname=fontname,
                fontsize=font_size,
                color=color,
                stroke_opacity=opacity,
                fill_opacity=opacity,
                rotate=page.rotation,
            )
    doc.save(str(output_path))
    doc.close()


def _text_baseline_y(rect: fitz.Rect, position: str, font_size: float) -> float:
    if position == "top":
        return rect.y0 + WATERMARK_MARGIN + font_size
    if position == "bottom":
        return rect.y1 - WATERMARK_MARGIN
    return (rect.y0 + rect.y1) / 2


def add_image_watermark(
    file: BinaryIO,
    output_path: Path,
    image: BinaryIO,
    position: str,
    opacity: float,
    width: int | None = None,
    pages: list[int] | None = None,
) -> None:
    doc = fitz.open(stream=file.read(), filetype="pdf")
    total = len(doc)
    targets = pages if pages else list(range(1, total + 1))
    image_bytes = image.read()
    size = width or 100

    if position == "diagonal":
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        rotated = pil_img.rotate(45, expand=True, fillcolor=(0, 0, 0, 0))
        buf = io.BytesIO()
        rotated.save(buf, format="PNG")
        image_bytes = buf.getvalue()

    for page_num in targets:
        if page_num < 1 or page_num > total:
            continue
        page = doc[page_num - 1]
        rect = page.rect
        x, y = _image_position(rect, position, size)
        img_rect = fitz.Rect(x, y, x + size, y + size)
        page.insert_image(img_rect, stream=image_bytes, overlay=True)
    doc.save(str(output_path))
    doc.close()


def _image_position(rect: fitz.Rect, position: str, size: int) -> tuple[float, float]:
    if position == "top":
        return (rect.x0 + rect.x1) / 2 - size / 2, rect.y0 + WATERMARK_MARGIN
    if position == "bottom":
        return (rect.x0 + rect.x1) / 2 - size / 2, rect.y1 - WATERMARK_MARGIN - size
    return (rect.x0 + rect.x1) / 2 - size / 2, (rect.y0 + rect.y1) / 2 - size / 2
