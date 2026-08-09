import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import BinaryIO

import fitz
import markdown as md_lib
from fastapi import HTTPException
from pdf2docx import Converter
from PIL import Image
from xhtml2pdf import pisa


def images_to_pdf(images: list[tuple[str, BinaryIO]], output_path: Path) -> None:
    pil_images: list[Image.Image] = []
    for _filename, img_file in images:
        img = Image.open(img_file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        pil_images.append(img)
    if not pil_images:
        raise HTTPException(status_code=400, detail="Aucune image valide.")
    first = pil_images[0]
    first.save(
        output_path,
        save_all=True,
        resolution=100.0,
        append_images=pil_images[1:],
    )


def pdf_to_images(
    file: BinaryIO,
    output_dir: Path,
    dpi: int = 150,
    fmt: str = "png",
) -> list[Path]:
    doc = fitz.open(stream=file.read(), filetype="pdf")
    fmt = fmt.lower()
    if fmt not in ("png", "jpg", "jpeg", "webp"):
        fmt = "png"
    paths: list[Path] = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat)
        ext = "jpg" if fmt == "jpeg" else fmt
        img_path = output_dir / f"page_{i + 1:04d}.{ext}"
        pix.save(str(img_path))
        paths.append(img_path)
    doc.close()
    return paths


def office_to_pdf(file: BinaryIO, output_dir: Path, original_name: str) -> Path:
    input_path = output_dir / original_name
    with open(input_path, "wb") as out:
        shutil.copyfileobj(file, out)

    if shutil.which("libreoffice") is None and shutil.which("soffice") is None:
        raise HTTPException(
            status_code=500, detail="LibreOffice n'est pas installé sur le serveur."
        )

    cmd = [
        "soffice",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(input_path),
    ]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504, detail="La conversion Office a dépassé le délai."
        ) from exc
    finally:
        try:
            input_path.unlink(missing_ok=True)
        except Exception:
            pass

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur LibreOffice: {result.stderr.decode('utf-8', errors='ignore')}",
        )

    base = Path(original_name).stem
    pdf_path = output_dir / f"{base}.pdf"
    if not pdf_path.exists():
        # LibreOffice may produce a different file name for some formats
        candidates = list(output_dir.glob("*.pdf"))
        if not candidates:
            raise HTTPException(
                status_code=500, detail="Fichier PDF converti introuvable."
            )
        pdf_path = candidates[0]
    return pdf_path


def pdf_to_word(file: BinaryIO, output_path: Path) -> None:
    input_path = output_path.with_suffix(".pdf")
    with open(input_path, "wb") as out:
        shutil.copyfileobj(file, out)
    try:
        converter = Converter(str(input_path))
        converter.convert(str(output_path), start=0, end=None)
        converter.close()
    finally:
        input_path.unlink(missing_ok=True)


# 1x1 transparent GIF, used to replace any non-data: URI so xhtml2pdf never
# performs a network request or reads a local file off disk.
_BLANK_PIXEL_URI = (
    "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
)


def _block_external_resources(uri: str, rel: str) -> str:
    """xhtml2pdf link_callback: only allow already-inline data: URIs through.

    Note: xhtml2pdf's pisaFileObject only substitutes the resolved URI when
    the callback returns a truthy value (see xhtml2pdf/files.py). Returning
    None/"" leaves the original URI untouched and xhtml2pdf will still fetch
    it, so blocking requires always returning something — here, either the
    original data: URI or a harmless inline placeholder.
    """
    if isinstance(uri, str) and uri.startswith("data:"):
        return uri
    return _BLANK_PIXEL_URI


def markdown_to_pdf(md_text: str, output_path: Path) -> None:
    html_body = md_lib.markdown(
        md_text, extensions=["extra", "nl2br", "sane_lists"]
    )
    html = f"""<html>
<head>
<style>
  body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; }}
  h1 {{ font-size: 20pt; }}
  h2 {{ font-size: 16pt; }}
  h3 {{ font-size: 13pt; }}
  code {{ font-family: Courier, monospace; background-color: #f0f0f0; }}
  pre {{ font-family: Courier, monospace; background-color: #f0f0f0; padding: 8px; }}
  blockquote {{ border-left: 2px solid #ccc; padding-left: 10px; color: #555555; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
    with open(output_path, "wb") as out:
        result = pisa.CreatePDF(
            html, dest=out, link_callback=_block_external_resources
        )
    if result.err:
        raise HTTPException(
            status_code=500, detail="Erreur lors de la génération du PDF."
        )


def build_zip(output_path: Path, files: list[Path]) -> None:
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            zf.write(file, arcname=file.name)
