"""Orchestrator — routes conversions to engines with quality checks and retry."""
from pathlib import Path
from typing import Optional

from allpdf.engines.base import ConversionEngine
from allpdf.engines.epub2pdf_engine import Epub2PdfEngine
from allpdf.engines.libreoffice import LibreOfficeEngine
from allpdf.engines.pdf2docx_engine import Pdf2DocxEngine
from allpdf.engines.pdf2xlsx_engine import Pdf2XlsxEngine
from allpdf.engines.pdf2pptx_engine import Pdf2PptxEngine
from allpdf.models import ConversionResult, ConversionStatus, FileFormat
from allpdf.quality.checker import QualityChecker


class Orchestrator:
    """Routes conversion requests to the appropriate engine.

    Handles engine selection, optional quality checking, and retry logic.
    """

    def __init__(self):
        self._engines: dict[tuple[FileFormat, FileFormat], ConversionEngine] = {}
        self._libreoffice = LibreOfficeEngine()
        self._register_engines()
        self._checker = QualityChecker()

    def _register_engines(self):
        """Register all available conversion engines."""
        for fmt in [FileFormat.DOCX, FileFormat.XLSX, FileFormat.PPTX]:
            self._engines[(fmt, FileFormat.PDF)] = self._libreoffice

        self._engines[(FileFormat.EPUB, FileFormat.PDF)] = Epub2PdfEngine()
        self._engines[(FileFormat.PDF, FileFormat.DOCX)] = Pdf2DocxEngine()
        self._engines[(FileFormat.PDF, FileFormat.XLSX)] = Pdf2XlsxEngine()
        self._engines[(FileFormat.PDF, FileFormat.PPTX)] = Pdf2PptxEngine()

    def convert(
        self,
        input_path: str,
        output_path: str,
        input_format: FileFormat | None = None,
        output_format: FileFormat | None = None,
        *,
        quality_check: bool = False,
        retry: int = 0,
        **options,
    ) -> ConversionResult:
        """Convert a file from one format to another."""
        if input_format is None:
            input_format = FileFormat.from_path(Path(input_path))
        if output_format is None:
            output_format = FileFormat.from_path(Path(output_path))

        engine = self._get_engine(input_format, output_format)
        if engine is None:
            return ConversionResult(
                input_path=Path(input_path), output_path=Path(output_path),
                input_format=input_format, output_format=output_format,
                status=ConversionStatus.FAILED, engine_used="none", duration_seconds=0,
                error_message=f"No engine available for {input_format.value} -> {output_format.value}",
            )

        if not engine.is_available():
            return ConversionResult(
                input_path=Path(input_path), output_path=Path(output_path),
                input_format=input_format, output_format=output_format,
                status=ConversionStatus.FAILED, engine_used=engine.name, duration_seconds=0,
                error_message=f"Engine '{engine.name}' is not available. Check dependencies.",
            )

        result = engine.convert(input_path, output_path, **options)

        if quality_check and result.status == ConversionStatus.SUCCESS:
            result.quality_report = self._checker.run(
                input_path, output_path, input_format, output_format,
            )

        if result.status == ConversionStatus.FAILED and retry > 0:
            for i in range(retry):
                alt = self._get_alternative(input_format, output_format)
                if alt:
                    result = alt.convert(input_path, output_path, **options)
                    result.retries = i + 1
                    if result.status == ConversionStatus.SUCCESS:
                        break

        return result

    def convert_auto(
        self, input_path: str, output_path: str, output_format: FileFormat, **options,
    ) -> ConversionResult:
        """Convert with auto-detected input format."""
        input_format = FileFormat.from_path(Path(input_path))
        return self.convert(input_path, output_path, input_format, output_format, **options)

    def list_engines(self) -> list[ConversionEngine]:
        """Return all registered engines."""
        return list(self._engines.values())

    def get_supported_conversions(self) -> list[dict]:
        """Return the conversion matrix with availability status."""
        return [
            {"from": src.value, "to": dst.value, "engine": engine.name, "available": engine.is_available()}
            for (src, dst), engine in self._engines.items()
        ]

    def _get_engine(self, src: FileFormat, dst: FileFormat) -> Optional[ConversionEngine]:
        key = (src, dst)
        if key in self._engines:
            engine = self._engines[key]
            if engine.name == "libreoffice" and not engine.accepts(src):
                return None
            return engine
        return None

    def _get_alternative(self, src: FileFormat, dst: FileFormat) -> Optional[ConversionEngine]:
        """Find an alternative engine (extensibility point)."""
        return None
