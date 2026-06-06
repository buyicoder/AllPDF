# allpdf/engines/libreoffice.py
"""LibreOffice engine — converts Office documents to PDF via headless mode."""
import os
import subprocess
import time
from pathlib import Path

from allpdf.engines.base import ConversionEngine
from allpdf.models import ConversionResult, ConversionStatus, FileFormat


class LibreOfficeEngine(ConversionEngine):
    """Convert Office documents to PDF using LibreOffice headless mode.

    Supports: DOCX, XLSX, PPTX (and legacy DOC, XLS, PPT) -> PDF.
    """

    name = "libreoffice"
    input_format = FileFormat.DOCX  # placeholder; set per-conversion
    output_format = FileFormat.PDF

    _supported_inputs = {FileFormat.DOCX, FileFormat.XLSX, FileFormat.PPTX}

    def accepts(self, fmt: FileFormat) -> bool:
        """Return True if this engine can convert the given format."""
        return fmt in self._supported_inputs

    def is_available(self) -> bool:
        """Check if LibreOffice soffice binary is on PATH."""
        try:
            result = subprocess.run(
                ["soffice", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def convert(self, input_path: str, output_path: str, **options) -> ConversionResult:
        input_fmt = FileFormat.from_path(Path(input_path))
        start = time.time()

        if not os.path.exists(input_path):
            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=input_fmt,
                output_format=FileFormat.PDF,
                status=ConversionStatus.FAILED,
                engine_used=self.name,
                duration_seconds=time.time() - start,
                error_message=f"Input file not found: {input_path}",
            )

        out_dir = os.path.dirname(output_path) or "."
        os.makedirs(out_dir, exist_ok=True)

        try:
            result = subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", out_dir,
                    input_path,
                ],
                capture_output=True, text=True, timeout=120,
            )

            duration = time.time() - start

            if result.returncode != 0:
                return ConversionResult(
                    input_path=Path(input_path),
                    output_path=Path(output_path),
                    input_format=input_fmt,
                    output_format=FileFormat.PDF,
                    status=ConversionStatus.FAILED,
                    engine_used=self.name,
                    duration_seconds=duration,
                    error_message=result.stderr.strip() or "LibreOffice conversion failed",
                )

            # LibreOffice names the output file based on the input stem
            generated_name = Path(input_path).stem + ".pdf"
            generated_path = os.path.join(out_dir, generated_name)

            if generated_path != output_path and os.path.exists(generated_path):
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(generated_path, output_path)

            if not os.path.exists(output_path):
                return ConversionResult(
                    input_path=Path(input_path),
                    output_path=Path(output_path),
                    input_format=input_fmt,
                    output_format=FileFormat.PDF,
                    status=ConversionStatus.FAILED,
                    engine_used=self.name,
                    duration_seconds=duration,
                    error_message="Output file was not created",
                )

            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=input_fmt,
                output_format=FileFormat.PDF,
                status=ConversionStatus.SUCCESS,
                engine_used=self.name,
                duration_seconds=duration,
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start
            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=input_fmt,
                output_format=FileFormat.PDF,
                status=ConversionStatus.FAILED,
                engine_used=self.name,
                duration_seconds=duration,
                error_message="Conversion timed out after 120 seconds",
            )
        except Exception as e:
            duration = time.time() - start
            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=input_fmt,
                output_format=FileFormat.PDF,
                status=ConversionStatus.FAILED,
                engine_used=self.name,
                duration_seconds=duration,
                error_message=str(e),
            )
