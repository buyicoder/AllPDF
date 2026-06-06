"""EPUB to PDF engine using ebooklib + PyMuPDF HTML rendering."""
import os
import time
from pathlib import Path
from html.parser import HTMLParser

import fitz
import ebooklib
from ebooklib import epub

from allpdf.engines.base import ConversionEngine
from allpdf.models import ConversionResult, ConversionStatus, FileFormat


class _EPubTextExtractor(HTMLParser):
    """Extract paragraph text from EPUB HTML content."""

    def __init__(self):
        super().__init__()
        self.paras = []
        self.skip = False
        self._cur = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip = True
        if tag in ("p", "div", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "br"):
            if self._cur:
                self.paras.append("".join(self._cur))
                self._cur = []

    def handle_endtag(self, tag):
        if tag in ("p", "div", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6"):
            if self._cur:
                self.paras.append("".join(self._cur))
                self._cur = []
        if tag in ("script", "style"):
            self.skip = False

    def handle_data(self, data):
        if not self.skip:
            t = data.strip()
            if t:
                self._cur.append(t)


class Epub2PdfEngine(ConversionEngine):
    """Convert EPUB e-books to PDF.

    Extracts text content from EPUB, then renders each page using
    PyMuPDF's HTML box for proper CJK and layout support.
    """

    name = "epub2pdf"
    input_format = FileFormat.EPUB
    output_format = FileFormat.PDF

    # Paragraphs per page — conservative estimate for 11pt text on A4
    PARAS_PER_PAGE = 25
    FONT_SIZE = 11
    LINE_HEIGHT = 1.55

    def convert(self, input_path: str, output_path: str, **options) -> ConversionResult:
        start = time.time()

        if not os.path.exists(input_path):
            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=FileFormat.EPUB,
                output_format=FileFormat.PDF,
                status=ConversionStatus.FAILED,
                engine_used=self.name,
                duration_seconds=time.time() - start,
                error_message=f"Input file not found: {input_path}",
            )

        try:
            book = epub.read_epub(input_path)

            title = book.get_metadata("DC", "title")
            title_text = title[0][0] if title else "Untitled"

            paras = [f"《{title_text}》", ""]
            for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                try:
                    content = item.get_content().decode("utf-8", errors="replace")
                    extractor = _EPubTextExtractor()
                    extractor.feed(content)
                    paras.extend(extractor.paras)
                except Exception:
                    pass

            p_tags = []
            for p in paras:
                p = p.strip()
                if p:
                    p = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    p_tags.append(f"<p>{p}</p>")

            para_per_page = options.get("paras_per_page", self.PARAS_PER_PAGE)

            pg_w, pg_h = 595, 842
            margin = 50
            rect = fitz.Rect(margin, margin, pg_w - margin, pg_h - margin)
            css = f"body{{font-family:sans-serif;font-size:{self.FONT_SIZE}pt;line-height:{self.LINE_HEIGHT}}}p{{margin:5px 0;text-indent:2em}}"

            doc = fitz.open()
            for i in range(0, len(p_tags), para_per_page):
                batch = p_tags[i : i + para_per_page]
                html = (
                    '<html><head><meta charset="utf-8"></head><body>'
                    + "\n".join(batch)
                    + "</body></html>"
                )
                page = doc.new_page(width=pg_w, height=pg_h)
                page.insert_htmlbox(rect, html, css=css)

            doc.save(output_path, garbage=4, deflate=True)
            page_count = doc.page_count
            doc.close()

            duration = time.time() - start

            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=FileFormat.EPUB,
                output_format=FileFormat.PDF,
                status=ConversionStatus.SUCCESS,
                engine_used=self.name,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.time() - start
            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=FileFormat.EPUB,
                output_format=FileFormat.PDF,
                status=ConversionStatus.FAILED,
                engine_used=self.name,
                duration_seconds=duration,
                error_message=str(e),
            )
