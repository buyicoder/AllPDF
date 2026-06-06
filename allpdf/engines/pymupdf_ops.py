# allpdf/engines/pymupdf_ops.py
"""PyMuPDF operations — PDF analysis and metadata extraction."""
import os
from pathlib import Path

import fitz

from allpdf.models import FileFormat, FileInfo


class PyMuPDFOps:
    """PDF analysis and manipulation operations using PyMuPDF.

    Not a ConversionEngine subclass — provides file analysis used by
    the orchestrator and quality checker. Does not convert between formats.
    """

    name = "pymupdf_ops"

    def analyze(self, filepath: str) -> FileInfo | None:
        """Analyze a PDF and return structured FileInfo.

        Returns None if the file does not exist or cannot be opened.
        """
        if not os.path.exists(filepath):
            return None

        path = Path(filepath)

        try:
            doc = fitz.open(filepath)
            page_count = doc.page_count

            image_count = 0
            text_length = 0
            for page in doc:
                image_count += len(page.get_images())
                text_length += len(page.get_text())

            # Heuristic: < 5 chars/page average → likely scanned
            avg_text = text_length / max(page_count, 1)
            is_scanned = avg_text < 5

            doc.close()

            return FileInfo(
                path=path,
                format=FileFormat.PDF,
                page_count=page_count,
                image_count=image_count,
                table_count=0,
                is_scanned=is_scanned,
                file_size_bytes=os.path.getsize(filepath),
            )
        except Exception:
            return None
