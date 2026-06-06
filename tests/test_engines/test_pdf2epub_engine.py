import os
from pathlib import Path
from zipfile import ZipFile
import fitz
from allpdf.engines.pdf2epub_engine import Pdf2EpubEngine
from allpdf.models import FileFormat


def _make_test_pdf(path: str, text: str = "Test PDF content for EPUB conversion."):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    doc.save(path)
    doc.close()


class TestPdf2EpubEngine:
    def test_engine_metadata(self):
        engine = Pdf2EpubEngine()
        assert engine.name == "pdf2epub"
        assert engine.input_format == FileFormat.PDF
        assert engine.output_format == FileFormat.EPUB
        assert engine.is_available() is True

    def test_convert_single_page_pdf(self, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        _make_test_pdf(str(pdf_path), "有限与无限的游戏测试。\n第二行文字。")

        epub_path = tmp_path / "test.epub"
        engine = Pdf2EpubEngine()
        result = engine.convert(str(pdf_path), str(epub_path))

        assert result.status.value == "success"
        assert os.path.exists(str(epub_path))
        assert os.path.getsize(str(epub_path)) > 0

        # Verify it's a valid EPUB (ZIP with mimetype)
        with ZipFile(str(epub_path)) as z:
            names = z.namelist()
            assert "mimetype" in names

    def test_convert_multipage_pdf(self, tmp_path):
        doc = fitz.open()
        for i in range(5):
            page = doc.new_page()
            page.insert_text((72, 72), f"Page {i+1} content for testing.", fontsize=12)
        pdf_path = tmp_path / "multi.pdf"
        doc.save(str(pdf_path))
        doc.close()

        epub_path = tmp_path / "multi.epub"
        engine = Pdf2EpubEngine()
        result = engine.convert(str(pdf_path), str(epub_path))

        assert result.status.value == "success"
        assert os.path.exists(str(epub_path))

    def test_convert_nonexistent_file(self, tmp_path):
        engine = Pdf2EpubEngine()
        result = engine.convert(
            str(tmp_path / "ghost.pdf"),
            str(tmp_path / "out.epub"),
        )
        assert result.status.value == "failed"
        assert result.error_message is not None
