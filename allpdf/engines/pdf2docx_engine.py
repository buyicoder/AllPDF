# allpdf/engines/pdf2docx_engine.py
"""PDF to DOCX engine using pdf2docx + PyMuPDF."""
import os
import time
from pathlib import Path

from pdf2docx import Converter

from allpdf.engines.base import ConversionEngine
from allpdf.models import ConversionResult, ConversionStatus, FileFormat


class Pdf2DocxEngine(ConversionEngine):
    """Convert PDF to DOCX using pdf2docx + PyMuPDF backend."""

    name = "pdf2docx"
    input_format = FileFormat.PDF
    output_format = FileFormat.DOCX

    def convert(self, input_path: str, output_path: str, **options) -> ConversionResult:
        start = time.time()

        if not os.path.exists(input_path):
            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=FileFormat.PDF,
                output_format=FileFormat.DOCX,
                status=ConversionStatus.FAILED,
                engine_used=self.name,
                duration_seconds=time.time() - start,
                error_message=f"Input file not found: {input_path}",
            )

        pages = options.get("pages", None)

        try:
            cv = Converter(input_path)
            cv.convert(output_path, pages=pages)
            cv.close()

            duration = time.time() - start

            if not os.path.exists(output_path):
                return ConversionResult(
                    input_path=Path(input_path),
                    output_path=Path(output_path),
                    input_format=FileFormat.PDF,
                    output_format=FileFormat.DOCX,
                    status=ConversionStatus.FAILED,
                    engine_used=self.name,
                    duration_seconds=duration,
                    error_message="Output file was not created",
                )

            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=FileFormat.PDF,
                output_format=FileFormat.DOCX,
                status=ConversionStatus.SUCCESS,
                engine_used=self.name,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.time() - start
            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=FileFormat.PDF,
                output_format=FileFormat.DOCX,
                status=ConversionStatus.FAILED,
                engine_used=self.name,
                duration_seconds=duration,
                error_message=str(e),
            )
