
from pathlib import Path

from backend.ingestion.file_processing.file_callings import process_document


TEST_FILES = Path("test_files")

for file_path in TEST_FILES.iterdir():

    if not file_path.is_file():
        continue

    with open(file_path, "rb") as file:
        file_bytes = file.read()

    result = process_document(file_bytes, file_path.name)

    print(f"\nFILE: {file_path.name}")
    print(f"STATUS: {result['status']}")

    if result["status"] == "success":
        print(f"TITLE: {result['title']}")
        print(f"FORMAT: {result['source_type']}")
        print(f"EXTRACTION METHOD: {result['extraction_method']}")
        print(f"CONTENT PREVIEW:\n{result['content'][:300]}")

    else:
        print(f"ERROR: {result.get('error')}")
