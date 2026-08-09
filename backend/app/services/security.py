from pathlib import Path
from typing import BinaryIO

import fitz
import pikepdf
from fastapi import HTTPException


def protect_pdf(
    file: BinaryIO,
    output_path: Path,
    user_password: str,
    owner_password: str | None = None,
    allow_printing: bool = True,
    allow_copying: bool = False,
) -> None:
    owner = owner_password or user_password
    pdf = pikepdf.open(file)
    pdf.save(
        str(output_path),
        encryption=pikepdf.Encryption(
            user=user_password,
            owner=owner,
            allow=pikepdf.Permissions(
                print_lowres=allow_printing,
                print_highres=allow_printing,
                extract=allow_copying,
            ),
        ),
    )
    pdf.close()


def unlock_pdf(
    file: BinaryIO,
    output_path: Path,
    password: str,
) -> None:
    try:
        pdf = pikepdf.open(file, password=password)
    except pikepdf.PasswordError as exc:
        raise HTTPException(status_code=422, detail="Mot de passe incorrect.") from exc
    pdf.save(str(output_path))
    pdf.close()


def redact_rectangles(
    file: BinaryIO,
    output_path: Path,
    rectangles: list[dict],
) -> None:
    doc = fitz.open(stream=file.read(), filetype="pdf")
    for item in rectangles:
        page_num = item.get("page", 1)
        rect = item.get("rect")
        if page_num < 1 or page_num > len(doc) or not rect:
            continue
        page = doc[page_num - 1]
        fitz_rect = fitz.Rect(rect["x1"], rect["y1"], rect["x2"], rect["y2"])
        page.add_redact_annot(fitz_rect, fill=(0, 0, 0))
        page.apply_redactions()
    doc.save(str(output_path))
    doc.close()


def search_and_redact(
    file: BinaryIO,
    output_path: Path,
    terms: list[str],
) -> None:
    doc = fitz.open(stream=file.read(), filetype="pdf")
    for page in doc:
        for term in terms:
            hits = page.search_for(term)
            for hit in hits:
                page.add_redact_annot(hit, fill=(0, 0, 0))
        page.apply_redactions()
    doc.save(str(output_path))
    doc.close()
