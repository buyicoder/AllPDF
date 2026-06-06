import os
from pathlib import Path
from zipfile import ZipFile
from allpdf.engines.epub2pdf_engine import Epub2PdfEngine
from allpdf.models import FileFormat


def _make_minimal_epub(path: str, title: str = "Test Book"):
    """Create a minimal valid EPUB file for testing."""
    with ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        )
        z.writestr(
            "content.opf",
            f'<?xml version="1.0"?><package version="2.0" xmlns="http://www.idpf.org/2007/opf">'
            f'<metadata><dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">{title}</dc:title></metadata>'
            f'<manifest><item id="ch1" href="ch1.html" media-type="application/xhtml+xml"/></manifest>'
            f'<spine><itemref idref="ch1"/></spine></package>',
        )
        z.writestr(
            "ch1.html",
            '<html><body><p>有限与无限的游戏测试。</p><p>这是第二段文字。</p></body></html>',
        )


class TestEpub2PdfEngine:
    def test_engine_metadata(self):
        engine = Epub2PdfEngine()
        assert engine.name == "epub2pdf"
        assert engine.input_format == FileFormat.EPUB
        assert engine.output_format == FileFormat.PDF
        assert engine.is_available() is True

    def test_convert_minimal_epub(self, tmp_path):
        epub_path = tmp_path / "test.epub"
        _make_minimal_epub(str(epub_path), title="测试书籍")

        pdf_path = tmp_path / "test.pdf"
        engine = Epub2PdfEngine()
        result = engine.convert(str(epub_path), str(pdf_path))

        assert result.status.value == "success"
        assert os.path.exists(str(pdf_path))
        assert os.path.getsize(str(pdf_path)) > 0

        # Verify content
        import fitz
        doc = fitz.open(str(pdf_path))
        text = doc[0].get_text()
        doc.close()
        assert len(text) > 10

    def test_convert_nonexistent_file(self, tmp_path):
        engine = Epub2PdfEngine()
        result = engine.convert(str(tmp_path / "ghost.epub"), str(tmp_path / "out.pdf"))
        assert result.status.value == "failed"
        assert result.error_message is not None
