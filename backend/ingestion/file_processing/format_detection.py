
from io import BytesIO
from pathlib import Path

import pymupdf
import pytesseract

from PIL import Image
from docx import Document


# --------------------------------------------------
# 1. COMMON METADATA GENERATOR
# --------------------------------------------------

def build_metadata(
    filename,
    source_type,
    content,
    extraction_method,
    page_count=None,
    extracted_pages=None,
    status=None,
    url=None
):
    title = Path(filename).stem
    if status is None:
        extracted_content = (
        content.split("\n", 1)[1].strip()
        if content.startswith("# ")
        else content.strip()
    )

    status = "success" if extracted_content else "empty"

    return {
        "url": url,
        "filename": filename,
        "title": title,
        "source_type": source_type,
        "page_count": page_count,
        "extracted_pages": extracted_pages,
        "extraction_method": sorted(set(extraction_method)),
        "status": status,
        "content": content
    }


# --------------------------------------------------
# 2. COMMON ERROR RESPONSE
# --------------------------------------------------

def failed_document(filename, source_type, error):
    return {
        "url": None,
        "filename": filename,
        "title": Path(filename).stem,
        "source_type": source_type,
        "page_count": None,
        "extracted_pages": None,
        "extraction_method": [],
        "status": "failed",
        "content": "",
        "error": str(error)
    }


# --------------------------------------------------
# 3. PDF EXTRACTION + OCR FALLBACK
# --------------------------------------------------

def process_pdf(file_bytes, filename, dpi=250):

    try:
        markdown_parts = [f"# {Path(filename).stem}\n"]
        extraction_methods = set()

        extracted_pages = 0

        with pymupdf.open(
            stream=file_bytes,
            filetype="pdf"
        ) as pdf:

            if pdf.needs_pass:
                raise ValueError("Password-protected PDF")

            page_count = len(pdf)

            if page_count == 0:
                raise ValueError("PDF contains no pages")

            for page_number, page in enumerate(pdf, start=1):

                text = page.get_text("text").strip()

                # OCR fallback for pages without selectable text
                if not text:

                    pix = page.get_pixmap(
                        dpi=dpi,
                        alpha=False
                    )

                    image = Image.frombytes(
                        "RGB",
                        [pix.width, pix.height],
                        pix.samples
                    )

                    text = pytesseract.image_to_string(
                        image
                    ).strip()

                    if text:
                        extraction_methods.add("tesseract_ocr")

                else:
                    extraction_methods.add("pymupdf")

                if text:
                    extracted_pages += 1

                    markdown_parts.append(
                        f"## Page {page_number}\n\n{text}\n"
                    )

        markdown = "\n".join(markdown_parts)

        return build_metadata(
            filename=filename,
            source_type="pdf",
            content=markdown,
            extraction_method=extraction_methods,
            page_count=page_count,
            extracted_pages=extracted_pages
        )

    except Exception as error:
        return failed_document(
            filename,
            "pdf",
            error
        )


# --------------------------------------------------
# 4. DOCX EXTRACTION + EMBEDDED IMAGE OCR
# --------------------------------------------------

def process_docx(file_bytes, filename):

    try:
        document = Document(BytesIO(file_bytes))

        content_parts = [
            f"# {Path(filename).stem}\n"
        ]

        extraction_methods = {"python-docx"}

        # Extract paragraphs
        for paragraph in document.paragraphs:

            text = paragraph.text.strip()

            if text:
                content_parts.append(text)

        # Extract tables
        for table in document.tables:

            for row in table.rows:

                row_text = " | ".join(
                    cell.text.strip()
                    for cell in row.cells
                )

                if row_text.strip():
                    content_parts.append(row_text)

        # Extract and OCR embedded images
        processed_images = set()

        for relationship in document.part.rels.values():

            if relationship.reltype.endswith("/image"):

                image_part = relationship.target_part

                image_id = str(image_part.partname)

                # Avoid processing duplicate image references
                if image_id in processed_images:
                    continue

                processed_images.add(image_id)

                image = Image.open(
                    BytesIO(image_part.blob)
                ).convert("RGB")

                image_text = pytesseract.image_to_string(
                    image
                ).strip()

                if image_text:

                    extraction_methods.add("tesseract_ocr")

                    content_parts.append(
                        f"\n## Extracted Image Text\n\n{image_text}"
                    )

        content = "\n\n".join(content_parts)

        return build_metadata(
            filename=filename,
            source_type="docx",
            content=content,
            extraction_method=extraction_methods
        )

    except Exception as error:
        return failed_document(
            filename,
            "docx",
            error
        )


# --------------------------------------------------
# 5. TXT EXTRACTION
# --------------------------------------------------

def process_txt(file_bytes, filename):

    try:
        text = file_bytes.decode("utf-8-sig").strip()

        content = (
            f"# {Path(filename).stem}\n\n{text}"
        )

        return build_metadata(
            filename=filename,
            source_type="txt",
            content=content,
            extraction_method={"direct_text"}
        )

    except Exception as error:
        return failed_document(
            filename,
            "txt",
            error
        )


# --------------------------------------------------
# 6. MARKDOWN EXTRACTION
# --------------------------------------------------

def process_md(file_bytes, filename):

    try:
        markdown = file_bytes.decode(
            "utf-8-sig"
        ).strip()

        content = (
            f"# {Path(filename).stem}\n\n{markdown}"
        )

        return build_metadata(
            filename=filename,
            source_type="md",
            content=content,
            extraction_method={"direct_markdown"}
        )

    except Exception as error:
        return failed_document(
            filename,
            "md",
            error
        )
