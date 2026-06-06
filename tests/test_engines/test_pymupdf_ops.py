# tests/test_engines/test_pymupdf_ops.py
import fitz
from pathlib import Path
from allpdf.engines.pymupdf_ops import PyMuPDFOps
from allpdf.models import FileFormat


def _make_test_pdf(path: str, text: str = "Test content"):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    doc.save(path)
    doc.close()


class TestPyMuPDFOps:
    def test_analyze_pdf(self, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        _make_test_pdf(str(pdf_path))

        ops = PyMuPDFOps()
        info = ops.analyze(str(pdf_path))

        assert info.format == FileFormat.PDF
        assert info.page_count == 1
        assert info.file_size_bytes > 0

    def test_analyze_nonexistent_file(self, tmp_path):
        ops = PyMuPDFOps()
        info = ops.analyze(str(tmp_path / "ghost.pdf"))
        assert info is None

    def test_is_scanned_detector(self, tmp_path):
        pdf_path = tmp_path / "text.pdf"
        _make_test_pdf(str(pdf_path), "Hello World")
        ops = PyMuPDFOps()
        info = ops.analyze(str(pdf_path))
        assert info.is_scanned is False
