# tests/test_engines/test_pdf2pptx_engine.py
import os
from pathlib import Path
import fitz
from allpdf.engines.pdf2pptx_engine import Pdf2PptxEngine
from allpdf.models import FileFormat


def _make_test_pdf(path: str, pages: int = 2):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Slide {i+1}", fontsize=18)
    doc.save(path)
    doc.close()


class TestPdf2PptxEngine:
    def test_engine_metadata(self):
        engine = Pdf2PptxEngine()
        assert engine.name == "pdf2pptx"
        assert engine.input_format == FileFormat.PDF
        assert engine.output_format == FileFormat.PPTX

    def test_convert_two_page_pdf(self, tmp_path):
        pdf_path = tmp_path / "slides.pdf"
        _make_test_pdf(str(pdf_path), pages=2)

        pptx_path = tmp_path / "slides.pptx"
        engine = Pdf2PptxEngine()
        result = engine.convert(str(pdf_path), str(pptx_path))

        assert result.status.value == "success"
        assert os.path.exists(str(pptx_path))
        assert os.path.getsize(str(pptx_path)) > 0

    def test_convert_single_page_pdf(self, tmp_path):
        pdf_path = tmp_path / "single.pdf"
        _make_test_pdf(str(pdf_path), pages=1)

        pptx_path = tmp_path / "single.pptx"
        engine = Pdf2PptxEngine()
        result = engine.convert(str(pdf_path), str(pptx_path))

        assert result.status.value == "success"
        assert os.path.exists(str(pptx_path))
