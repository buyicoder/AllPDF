"""PDF to EPUB engine using PyMuPDF text extraction + ebooklib EPUB creation.

For scanned/image-based PDFs, renders pages as images and embeds them.
For text-based PDFs, extracts text directly.
"""
import base64
import os
import tempfile
import time
from pathlib import Path

import fitz
from ebooklib import epub

from allpdf.engines.base import ConversionEngine
from allpdf.models import ConversionResult, ConversionStatus, FileFormat


class Pdf2EpubEngine(ConversionEngine):
    """Convert PDF to EPUB e-book.

    Auto-detects scanned PDFs and switches to image-based rendering.
    """

    name = "pdf2epub"
    input_format = FileFormat.PDF
    output_format = FileFormat.EPUB

    # DPI for rendering scanned pages
    IMAGE_DPI = 150

    def convert(self, input_path: str, output_path: str, **options) -> ConversionResult:
        start = time.time()

        if not os.path.exists(input_path):
            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=FileFormat.PDF,
                output_format=FileFormat.EPUB,
                status=ConversionStatus.FAILED,
                engine_used=self.name,
                duration_seconds=time.time() - start,
                error_message=f"Input file not found: {input_path}",
            )

        try:
            pdf_doc = fitz.open(input_path)
            page_count = pdf_doc.page_count

            # Detect if this is a scanned PDF
            total_text = sum(len(pdf_doc[p].get_text()) for p in range(min(10, page_count)))
            is_scanned = total_text < 100

            book = epub.EpubBook()
            book.set_identifier(f"allpdf-{int(time.time())}")
            book.set_title(Path(input_path).stem)
            book.set_language("zh-CN")
            book.add_author("Converted by AllPDF")

            style_content = (
                "body{font-family:serif;font-size:1em;line-height:1.8;margin:1em}"
                "p{text-indent:2em;margin:0.5em 0}h1,h2{text-align:center}"
                "img{max-width:100%;height:auto;display:block;margin:0 auto}"
            )
            style = epub.EpubItem(
                uid="style", file_name="style/default.css",
                media_type="text/css", content=style_content,
            )
            book.add_item(style)

            spine = ["nav"]
            toc = []
            chapters = []

            if is_scanned:
                chapters = self._build_image_chapters(
                    pdf_doc, page_count, book, style, spine, toc, options
                )
            else:
                chapters = self._build_text_chapters(
                    pdf_doc, page_count, book, style, spine, toc, options
                )

            book.toc = toc
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            book.spine = spine

            pdf_doc.close()
            epub.write_epub(output_path, book)

            duration = time.time() - start
            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=FileFormat.PDF,
                output_format=FileFormat.EPUB,
                status=ConversionStatus.SUCCESS,
                engine_used=self.name,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.time() - start
            return ConversionResult(
                input_path=Path(input_path),
                output_path=Path(output_path),
                input_format=FileFormat.PDF,
                output_format=FileFormat.EPUB,
                status=ConversionStatus.FAILED,
                engine_used=self.name,
                duration_seconds=duration,
                error_message=str(e),
            )

    def _build_text_chapters(self, pdf_doc, page_count, book, style, spine, toc, options):
        """Build chapters from extractable text."""
        chapters = []
        pages_per_chapter = options.get("pages_per_chapter", 5)

        for i in range(0, page_count, pages_per_chapter):
            chapter_pages = range(i, min(i + pages_per_chapter, page_count))
            parts = []
            for pn in chapter_pages:
                text = pdf_doc[pn].get_text()
                if text.strip():
                    parts.append(f'<p class="page-num">—— 第{pn+1}页 ——</p>')
                    for para in text.strip().split("\n"):
                        para = para.strip()
                        if para:
                            para = para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            parts.append(f"<p>{para}</p>")
            if not parts:
                continue

            cn = len(chapters) + 1
            ch = epub.EpubHtml(
                title=f"Chapter {cn}", file_name=f"chap_{cn:03d}.xhtml", lang="zh-CN",
            )
            ch.content = f"<h2>Chapter {cn}</h2>\n" + "\n".join(parts)
            ch.add_item(style)
            book.add_item(ch)
            chapters.append(ch)
            spine.append(ch)
            toc.append(epub.Link(f"chap_{cn:03d}.xhtml", f"Chapter {cn}", f"ch{cn}"))

        if not chapters:
            ch = epub.EpubHtml(title="Content", file_name="chap_001.xhtml", lang="zh-CN")
            ch.content = "<p>No extractable text found.</p>"
            ch.add_item(style)
            book.add_item(ch)
            chapters.append(ch)
            spine.append(ch)

        return chapters

    def _build_image_chapters(self, pdf_doc, page_count, book, style, spine, toc, options):
        """Build chapters from rendered page images (for scanned PDFs)."""
        chapters = []
        dpi = options.get("dpi", self.IMAGE_DPI)
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        pages_per_chapter = options.get("pages_per_chapter", 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(0, page_count, pages_per_chapter):
                chapter_pages = list(range(i, min(i + pages_per_chapter, page_count)))
                img_tags = []

                for pn in chapter_pages:
                    page = pdf_doc[pn]
                    pix = page.get_pixmap(matrix=mat)
                    img_path = os.path.join(tmpdir, f"page_{pn:04d}.png")
                    pix.save(img_path)

                    # Read image and embed as base64 in HTML
                    with open(img_path, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode()
                    img_tags.append(
                        f'<div class="page"><p class="page-num">Page {pn+1}</p>'
                        f'<img src="data:image/png;base64,{img_b64}" alt="Page {pn+1}"/></div>'
                    )

                cn = len(chapters) + 1
                ch = epub.EpubHtml(
                    title=f"Page {i+1}",
                    file_name=f"chap_{cn:03d}.xhtml",
                    lang="zh-CN",
                )
                ch.content = f"<h2>Page {i+1}</h2>\n" + "\n".join(img_tags)
                ch.add_item(style)
                book.add_item(ch)
                chapters.append(ch)
                spine.append(ch)
                toc.append(epub.Link(f"chap_{cn:03d}.xhtml", f"Page {i+1}", f"ch{cn}"))

        return chapters
