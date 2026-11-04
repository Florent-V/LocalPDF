import zipfile
from pathlib import Path


def build_zip(output_path: Path, files: list[Path]) -> None:
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            zf.write(file, arcname=file.name)
