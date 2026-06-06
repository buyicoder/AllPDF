# tests/test_engines/test_libreoffice.py
import os
import subprocess
from pathlib import Path
import pytest
from allpdf.engines.libreoffice import LibreOfficeEngine
from allpdf.models import FileFormat


def _has_libreoffice():
    try:
        result = subprocess.run(["soffice", "--version"], capture_output=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


requires_libreoffice = pytest.mark.skipif(
    not _has_libreoffice(),
    reason="LibreOffice is not installed or not on PATH",
)


class TestLibreOfficeEngine:
    def test_engine_metadata(self):
        engine = LibreOfficeEngine()
        assert engine.name == "libreoffice"
        assert engine.input_format in (FileFormat.DOCX, FileFormat.XLSX, FileFormat.PPTX)
        assert engine.output_format == FileFormat.PDF

    def test_is_available_checks_soffice(self):
        engine = LibreOfficeEngine()
        available = engine.is_available()
        assert isinstance(available, bool)

    @requires_libreoffice
    def test_convert_docx_to_pdf(self, tmp_path):
        from docx import Document
        docx_path = tmp_path / "test.docx"
        d = Document()
        d.add_paragraph("Hello AllPDF")
        d.save(str(docx_path))

        pdf_path = tmp_path / "test.pdf"
        engine = LibreOfficeEngine()
        result = engine.convert(str(docx_path), str(pdf_path))

        assert result.status.value == "success"
        assert os.path.exists(str(pdf_path))
        assert os.path.getsize(str(pdf_path)) > 0

    def test_convert_nonexistent_file_returns_failed(self, tmp_path):
        engine = LibreOfficeEngine()
        result = engine.convert(
            str(tmp_path / "nonexistent.docx"),
            str(tmp_path / "out.pdf"),
        )
        assert result.status.value == "failed"
        assert result.error_message is not None
