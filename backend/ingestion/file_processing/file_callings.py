
from pathlib import Path

from .format_detection import (
    process_pdf,
    process_docx,
    process_txt,
    process_md
)


SUPPORTED_FORMATS = {
    ".pdf": process_pdf,
    ".docx": process_docx,
    ".txt": process_txt,
    ".md": process_md
}


def process_document(file_bytes: bytes, filename: str) -> dict:
    """
    Detect the uploaded file format and call
    the appropriate extraction function.
    """

    extension = Path(filename).suffix.lower()

    processor = SUPPORTED_FORMATS.get(extension)

    if processor is None:
        return {
            "status": "unsupported",
            "filename": filename,
            "error": (
                "The file type uploaded is not supported. "
                "Only these types are supported: "
                "PDF, MD, DOCX and TXT."
            )
        }

    return processor(file_bytes, filename)
