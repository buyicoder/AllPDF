# tests/test_engines/test_pdf2docx_engine.py
import os
from pathlib import Path
import fitz
from allpdf.engines.pdf2docx_engine import Pdf2DocxEngine
from allpdf.models import FileFormat


def _make_test_pdf(path: str, text: str = "Hello World from AllPDF"):
    """Helper to create a minimal PDF for testing."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    doc.save(path)
    doc.close()


class TestPdf2DocxEngine:
    def test_engine_metadata(self):
        engine = Pdf2DocxEngine()
        assert engine.name == "pdf2docx"
        assert engine.input_format == FileFormat.PDF
        assert engine.output_format == FileFormat.DOCX

    def test_convert_simple_pdf(self, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        _make_test_pdf(str(pdf_path))

        docx_path = tmp_path / "test.docx"
        engine = Pdf2DocxEngine()
        result = engine.convert(str(pdf_path), str(docx_path))

        assert result.status.value == "success"
        assert os.path.exists(str(docx_path))
        assert os.path.getsize(str(docx_path)) > 0

    def test_convert_nonexistent_pdf_fails(self, tmp_path):
        engine = Pdf2DocxEngine()
        result = engine.convert(
            str(tmp_path / "ghost.pdf"),
            str(tmp_path / "out.docx"),
        )
        assert result.status.value == "failed"
