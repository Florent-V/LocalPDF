from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader, PdfWriter


def inspect_form(file: BinaryIO) -> list[dict]:
    reader = PdfReader(file)
    fields = reader.get_fields()
    if not fields:
        return []

    result = []
    for name, field in fields.items():
        result.append(
            {
                "name": name,
                "type": field.get("/FT", "").replace("/", ""),
                "value": field.get("/V", ""),
                "options": [str(opt) for opt in field.get("/Opt", [])],
            }
        )
    return result


def fill_form(
    file: BinaryIO,
    output_path: Path,
    values: dict[str, str],
    flatten: bool = False,
) -> None:
    reader = PdfReader(file)
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)

    for page in writer.pages:
        if "/Annots" not in page:
            continue
        for annot in page["/Annots"]:
            field = annot.get_object()
            field_name = field.get("/T")
            if field_name and field_name in values:
                field.update({"/V": values[field_name]})
                if flatten:
                    field.update({"/Ff": 1})

    with open(output_path, "wb") as out:
        writer.write(out)
