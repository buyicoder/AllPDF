# tests/test_engines/test_pdf2xlsx_engine.py
import os
from pathlib import Path
import fitz
from allpdf.engines.pdf2xlsx_engine import Pdf2XlsxEngine
from allpdf.models import FileFormat


def _make_pdf_with_table(path: str):
    """Create a PDF with a simple tabular structure."""
    doc = fitz.open()
    page = doc.new_page()
    page.draw_line((50, 50), (200, 50))
    page.draw_line((50, 70), (200, 70))
    page.draw_line((50, 50), (50, 70))
    page.draw_line((200, 50), (200, 70))
    page.insert_text((60, 65), "A1", fontsize=10)
    page.insert_text((130, 65), "B1", fontsize=10)
    doc.save(path)
    doc.close()


class TestPdf2XlsxEngine:
    def test_engine_metadata(self):
        engine = Pdf2XlsxEngine()
        assert engine.name == "pdf2xlsx"
        assert engine.input_format == FileFormat.PDF
        assert engine.output_format == FileFormat.XLSX

    def test_convert_pdf_with_table(self, tmp_path):
        pdf_path = tmp_path / "table.pdf"
        _make_pdf_with_table(str(pdf_path))

        xlsx_path = tmp_path / "table.xlsx"
        engine = Pdf2XlsxEngine()
        result = engine.convert(str(pdf_path), str(xlsx_path))

        assert result.status.value == "success"
        assert os.path.exists(str(xlsx_path))
        assert os.path.getsize(str(xlsx_path)) > 0

    def test_convert_empty_pdf(self, tmp_path):
        doc = fitz.open()
        doc.new_page()
        pdf_path = tmp_path / "empty.pdf"
        doc.save(str(pdf_path))
        doc.close()

        xlsx_path = tmp_path / "empty.xlsx"
        engine = Pdf2XlsxEngine()
        result = engine.convert(str(pdf_path), str(xlsx_path))

        assert result.status.value == "success"
        assert os.path.exists(str(xlsx_path))
