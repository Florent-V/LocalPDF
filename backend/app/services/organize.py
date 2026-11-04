import base64
from pathlib import Path
from typing import BinaryIO

import fitz
from fastapi import HTTPException
from pypdf import PdfReader, PdfWriter


def merge_pdfs(files: list[tuple[str, BinaryIO]], output_path: Path) -> None:
    """Fusionne une liste de PDF dans l'ordre donné."""
    writer = PdfWriter()
    for _filename, file in files:
        reader = PdfReader(file)
        for page in reader.pages:
            writer.add_page(page)
    with open(output_path, "wb") as out:
        writer.write(out)


def split_pdf(
    file: BinaryIO, output_dir: Path, ranges: list[tuple[int, int]] | None = None
) -> list[Path]:
    """Découpe un PDF selon des plages 1-indexées ou une page par fichier."""
    reader = PdfReader(file)
    total = len(reader.pages)
    if total == 0:
        raise HTTPException(status_code=400, detail="Le PDF est vide.")

    if ranges is None:
        ranges = [(i, i) for i in range(1, total + 1)]

    output_files: list[Path] = []
    for index, (start, end) in enumerate(ranges, start=1):
        start = max(1, start)
        end = min(total, end)
        if start > end:
            continue
        writer = PdfWriter()
        for page_num in range(start - 1, end):
            writer.add_page(reader.pages[page_num])
        out_path = output_dir / f"split_{index:04d}.pdf"
        with open(out_path, "wb") as out:
            writer.write(out)
        output_files.append(out_path)
    return output_files


def generate_thumbnails(pdf_path: Path, output_dir: Path, dpi: int = 100) -> list[str]:
    """Génère des miniatures PNG et retourne des data URLs base64."""
    doc = fitz.open(str(pdf_path))
    data_urls: list[str] = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        b64 = base64.b64encode(png_bytes).decode("ascii")
        data_urls.append(f"data:image/png;base64,{b64}")
    doc.close()
    return data_urls


def reorder_and_delete_pages(
    input_path: Path,
    output_path: Path,
    new_order: list[int],
    rotations: dict[int, int] | None = None,
) -> None:
    """Réordonne/conserve les pages selon new_order (indices 1-indexés).

    rotations mappe un numéro de page ORIGINAL (avant réordonnancement) vers
    un delta de rotation en degrés, appliqué à la page correspondante.
    """
    writer = PdfWriter()
    reader = PdfReader(input_path)
    total = len(reader.pages)
    for page_num in new_order:
        if 1 <= page_num <= total:
            written_page = writer.add_page(reader.pages[page_num - 1])
            delta = (rotations or {}).get(page_num)
            if delta:
                written_page.rotate(delta % 360)
    with open(output_path, "wb") as out:
        writer.write(out)
