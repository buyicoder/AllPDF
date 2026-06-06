"""PDF to EPUB engine using PyMuPDF text extraction + ebooklib EPUB creation.

Scanned/image-based PDFs: renders pages as images and embeds them as proper
EPUB image assets (e-reader compatible).
Text-based PDFs: extracts text directly.
"""
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
    Each page image is registered as a proper EPUB asset, referenced
    by relative path — readable by any EPUB reader.
    """

    name = "pdf2epub"
    input_format = FileFormat.PDF
    output_format = FileFormat.EPUB

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

            # Detect scanned PDF
            total_text = sum(len(pdf_doc[p].get_text()) for p in range(min(10, page_count)))
            is_scanned = total_text < 100

            book = epub.EpubBook()
            book.set_identifier(f"allpdf-{int(time.time())}")
            book.set_title(Path(input_path).stem)
            book.set_language("zh-CN")
            book.add_author("Converted by AllPDF")

            style_content = (
                "body{font-family:serif;font-size:1em;line-height:1.8;margin:0}"
                "img{max-width:100%;height:auto;display:block;margin:0;padding:0}"
                ".page{margin:0;padding:0}"
            )
            style = epub.EpubItem(
                uid="style", file_name="style/default.css",
                media_type="text/css", content=style_content,
            )
            book.add_item(style)

            spine = ["nav"]
            toc = []

            force_image = options.get("force_image", False)
            use_hybrid = options.get("hybrid", False)
            use_ocr = options.get("ocr", False)

            if force_image:
                dpi = options.get("dpi", self.IMAGE_DPI)
                self._build_image_chapters(
                    pdf_doc, page_count, book, style, spine, toc, dpi, options,
                )
            elif use_ocr:
                # OCR hybrid: text for body, cropped images for formula regions
                self._build_ocr_hybrid_chapters(
                    pdf_doc, page_count, book, style, spine, toc, options,
                )
            elif use_hybrid:
                # Page-level hybrid: text pages → text, formula/diagram pages → images
                self._build_page_hybrid_chapters(
                    pdf_doc, page_count, book, style, spine, toc, options,
                )
            elif is_scanned:
                dpi = options.get("dpi", self.IMAGE_DPI)
                self._build_image_chapters(
                    pdf_doc, page_count, book, style, spine, toc, dpi, options,
                )
            else:
                self._build_text_chapters(
                    pdf_doc, page_count, book, style, spine, toc, options,
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

    def _build_image_chapters(self, pdf_doc, page_count, book, style, spine, toc,
                              dpi, options):
        """Build chapters from rendered page images (for scanned PDFs)."""
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pages_per_chapter = options.get("pages_per_chapter", 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(0, page_count, pages_per_chapter):
                chapter_pages = list(range(i, min(i + pages_per_chapter, page_count)))
                img_tags = []

                for pn in chapter_pages:
                    page = pdf_doc[pn]
                    pix = page.get_pixmap(matrix=mat)
                    img_filename = f"page_{pn:04d}.png"
                    img_path = os.path.join(tmpdir, img_filename)
                    pix.save(img_path)

                    with open(img_path, "rb") as f:
                        img_data = f.read()
                    epub_img = epub.EpubImage()
                    epub_img.file_name = f"images/{img_filename}"
                    epub_img.media_type = "image/png"
                    epub_img.content = img_data
                    book.add_item(epub_img)

                    img_tags.append(
                        f'<div class="page">'
                        f'<img src="images/{img_filename}" alt="Page {pn+1}"/>'
                        f'</div>'
                    )

                cn = len(toc) + 1
                ch = epub.EpubHtml(
                    title=f"Page {i+1}",
                    file_name=f"chap_{cn:03d}.xhtml",
                    lang="zh-CN",
                )
                ch.content = "\n".join(img_tags)
                ch.add_item(style)
                book.add_item(ch)
                spine.append(ch)
                toc.append(epub.Link(f"chap_{cn:03d}.xhtml", f"Page {i+1}", f"ch{cn}"))

    def _build_ocr_hybrid_chapters(self, pdf_doc, page_count, book, style, spine, toc, options):
        """Build EPUB with high-quality OCR hybrid: text for body, images for formulas.

        Uses 200 DPI, image preprocessing (contrast+sharpness), and math-symbol
        detection to minimize false image conversions.
        """
        import io as _io
        import re as _re
        import sys as _sys
        import easyocr
        from PIL import Image as _Image, ImageEnhance

        dpi = options.get("dpi", 200)
        threshold = options.get("text_confidence", 0.3)
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        # Math-heavy pattern: if text contains many math symbols, treat as formula
        _math_pattern = _re.compile(r'[=+\-\*/\(\)\[\]\{\}^_\\∑∫∏√∞∂∇∆±≤≥<>|~]')

        print(f"  Loading EasyOCR (Chinese + English)...", file=_sys.stderr)
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, verbose=False)
        print(f"  OCR: {page_count} pages, {dpi} DPI, threshold={threshold}", file=_sys.stderr)

        img_counter = 0
        for pn in range(page_count):
            page = pdf_doc[pn]
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")

            # Preprocess: enhance contrast + sharpen for better OCR
            pil_img = _Image.open(_io.BytesIO(img_bytes))
            enhancer = ImageEnhance.Contrast(pil_img)
            pil_img = enhancer.enhance(1.5)
            enhancer = ImageEnhance.Sharpness(pil_img)
            pil_img = enhancer.enhance(2.0)
            buf = _io.BytesIO()
            pil_img.save(buf, format="PNG")
            processed_bytes = buf.getvalue()

            results = reader.readtext(processed_bytes)

            if not results:
                img_counter += 1
                img_name = f"img_{img_counter:05d}.png"
                epub_img = epub.EpubImage()
                epub_img.file_name = f"images/{img_name}"
                epub_img.media_type = "image/png"
                epub_img.content = img_bytes  # Use original (cleaner) image
                book.add_item(epub_img)

                ch = epub.EpubHtml(
                    title=f"Page {pn+1}",
                    file_name=f"chap_{pn+1:03d}.xhtml", lang="zh-CN",
                )
                ch.content = f'<div class="page"><img src="images/{img_name}" alt="Page {pn+1}"/></div>'
                ch.add_item(style)
                book.add_item(ch)
                spine.append(ch)
                toc.append(epub.Link(f"chap_{pn+1:03d}.xhtml", f"Page {pn+1}", f"ch{pn+1}"))
                continue

            results.sort(key=lambda r: (r[0][0][1], r[0][0][0]))

            html_parts = []
            for bbox, text, conf in results:
                t = text.strip()
                if not t:
                    continue

                # Classify: text vs formula
                math_score = len(_math_pattern.findall(t))
                is_math_heavy = math_score >= 3 or (len(t) < 10 and math_score >= 1)
                is_low_conf = conf < threshold

                if is_math_heavy or is_low_conf:
                    # Formula/symbol region → embed as cropped image
                    x1 = max(0, int(bbox[0][0]) - 3)
                    y1 = max(0, int(bbox[0][1]) - 3)
                    x2 = min(pix.width, int(bbox[2][0]) + 3)
                    y2 = min(pix.height, int(bbox[2][1]) + 3)

                    # Validate coordinates
                    if x2 <= x1 or y2 <= y1:
                        # Invalid bbox — fall through to text
                        t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        html_parts.append(f"<p>{t}</p>")
                        continue

                    # Crop from ORIGINAL image (not processed) for visual quality
                    orig_img = _Image.open(_io.BytesIO(img_bytes))
                    crop = orig_img.crop((x1, y1, x2, y2))
                    crop_buf = _io.BytesIO()
                    crop.save(crop_buf, format="PNG")
                    crop_data = crop_buf.getvalue()

                    img_counter += 1
                    img_name = f"img_{img_counter:05d}.png"
                    epub_img = epub.EpubImage()
                    epub_img.file_name = f"images/{img_name}"
                    epub_img.media_type = "image/png"
                    epub_img.content = crop_data
                    book.add_item(epub_img)

                    html_parts.append(
                        f'<div class="formula">'
                        f'<img src="images/{img_name}" alt="formula"/>'
                        f'</div>'
                    )
                else:
                    # High confidence text → HTML paragraph
                    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    html_parts.append(f"<p>{t}</p>")

            if not html_parts:
                continue

            ch = epub.EpubHtml(
                title=f"Page {pn+1}",
                file_name=f"chap_{pn+1:03d}.xhtml", lang="zh-CN",
            )
            ch.content = "\n".join(html_parts)
            ch.add_item(style)
            book.add_item(ch)
            spine.append(ch)
            toc.append(epub.Link(f"chap_{pn+1:03d}.xhtml", f"Page {pn+1}", f"ch{pn+1}"))

            if (pn + 1) % 25 == 0:
                pct = (pn + 1) * 100 // page_count
                print(f"  Page {pn+1}/{page_count} ({pct}%), {img_counter} images", file=_sys.stderr)

            print(f"  OCR done. {img_counter} formula images embedded.", file=_sys.stderr)

    def _build_text_chapters(self, pdf_doc, page_count, book, style, spine, toc, options):
        """Build chapters with structured paragraph merging.

        Uses ``get_text("dict")`` to get bbox, font, and size for every text span.
        Merges consecutive lines into proper paragraphs based on line spacing
        and font consistency. Detects headings from font size.
        """
        pages_per_chapter = options.get("pages_per_chapter", 5)

        for i in range(0, page_count, pages_per_chapter):
            chapter_pages = range(i, min(i + pages_per_chapter, page_count))
            all_html = []

            for pn in chapter_pages:
                page_html = self._render_page_as_html(pdf_doc[pn])
                if page_html:
                    all_html.append(page_html)

            if not all_html:
                continue

            cn = len(toc) + 1
            ch = epub.EpubHtml(
                title=f"Chapter {cn}", file_name=f"chap_{cn:03d}.xhtml", lang="zh-CN",
            )
            ch.content = "\n".join(all_html)
            ch.add_item(style)
            book.add_item(ch)
            spine.append(ch)
            toc.append(epub.Link(f"chap_{cn:03d}.xhtml", f"Chapter {cn}", f"ch{cn}"))

    # ------------------------------------------------------------------
    # Structured page rendering — the core of the rewrite
    # ------------------------------------------------------------------

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape text for safe HTML embedding."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _render_page_as_html(self, page) -> str | None:
        """Convert a single PDF page to HTML using structured text data.

        Returns a string of HTML (a mix of <h1>, <h2>, <p>, <pre>), or None
        if the page has no extractable content.
        """
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        blocks = text_dict.get("blocks", [])

        if not blocks:
            return None

        # Step 1: collect all text spans with position info, sorted top→bottom
        entries = []  # list of {y, x, text, font, size, bbox}
        for block in blocks:
            if block.get("type") != 0:  # image block
                continue
            for line in block.get("lines", []):
                bbox = line["bbox"]  # (x0, y0, x1, y1)
                line_spans = []
                y_top = bbox[1]
                x_start = bbox[0]
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if text.strip():
                        line_spans.append({
                            "y": y_top,
                            "x": x_start,
                            "text": text,
                            "font": span.get("font", ""),
                            "size": span.get("size", 0),
                        })
                if line_spans:
                    # Join spans on the same line, preserving spaces
                    merged_text = "".join(s["text"] for s in line_spans)
                    rep = line_spans[0]
                    entries.append({
                        "y": rep["y"],
                        "text": merged_text.strip(),
                        "font": rep["font"],
                        "size": rep["size"],
                    })

        if not entries:
            return None

        # Step 2: compute dominant font size (the "body text" size)
        sizes = [e["size"] for e in entries]
        if not sizes:
            return None
        body_size = max(set(sizes), key=sizes.count)  # most common size

        # Step 3: compute median line spacing
        spacings = []
        for j in range(1, len(entries)):
            gap = entries[j]["y"] - entries[j - 1]["y"]
            if 0 < gap < 50:  # ignore huge gaps (block boundaries)
                spacings.append(gap)
        median_gap = sorted(spacings)[len(spacings) // 2] if spacings else body_size * 1.2

        # Step 4: merge lines into paragraphs, detect headings
        para_gap_threshold = median_gap * 1.6  # gap > 1.6x normal → new paragraph
        html_parts = []
        para_lines = []

        def _flush_paragraph():
            if not para_lines:
                return
            # Determine tag
            line_sizes = [ln["size"] for ln in para_lines]
            avg_size = sum(line_sizes) / len(line_sizes)
            full_text = "".join(ln["text"] for ln in para_lines)

            if avg_size >= body_size * 1.3 and len(full_text) < 80:
                # Larger font + short → heading
                if avg_size >= body_size * 1.6:
                    tag = "h1"
                else:
                    tag = "h2"
                html_parts.append(
                    f"<{tag}>{self._escape_html(full_text)}</{tag}>"
                )
            else:
                html_parts.append(
                    f"<p>{self._escape_html(full_text)}</p>"
                )
            para_lines.clear()

        for j, entry in enumerate(entries):
            if j == 0:
                para_lines.append(entry)
                continue

            prev = entries[j - 1]
            gap = entry["y"] - prev["y"]
            same_font = entry["font"] == prev["font"]
            similar_size = abs(entry["size"] - prev["size"]) < 2

            # Check if new paragraph
            is_new_para = False

            # Large gap → new paragraph
            if gap > para_gap_threshold:
                is_new_para = True

            # Font size jumps up significantly → heading → new paragraph
            if entry["size"] >= body_size * 1.3 and len(entry["text"]) < 60:
                is_new_para = True

            if is_new_para:
                _flush_paragraph()

            para_lines.append(entry)

        _flush_paragraph()

        return "\n".join(html_parts) if html_parts else None

    # ------------------------------------------------------------------
    # Hybrid text+image builder (no OCR dependency — uses PyMuPDF fonts)
    # ------------------------------------------------------------------

    # Font names that indicate math/symbol content
    _MATH_FONT_PATTERNS = [
        "math", "symbol", "cmmi", "cmsy", "cmex", "msam", "msbm",
        "euler", "eufm", "eurm", "rsfs", "wasy", "stmary",
        "mt2mit", "mt2syt", "msxm", "msym",
    ]

    # Characters that STRONGLY indicate math content (not common punctuation)
    # Excludes: = + - ( ) [ ] { } < > | ~ / * which are too common in prose
    _MATH_CHAR_PATTERN = (
        r'[∑∫∏√∞∂∇∆±'
        r'∀∃∈∉⊂⊃⊆⊇∪∩∧∨⇒⇔→←↑↓↔'
        r'αβγδεζηθικλμνξπρστυφχψω'
        r'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΠΡΣΤΥΦΧΨΩ'
        r'∅ℕℤℚℝℂℍ'
        r'≅≆≇≈≉≊≋≌≍≎≏≐≑≒≓≔≕≖≗≘≙≚≛≜≝≞≟'
        r'≠≡≤≥≪≫≬≭≮≯≰≱≲≳≴≵≶≷≸≹'
        r'⊕⊗⊖⊘⊚⊛⊜⊝⊞⊟⊠⊡'
        r'∣∤∥∦∧∨∩∪∫∬∭∮∯∰∱∲∳∴∵∶∷∸∹∺∻∼∽∾∿'
        r'ƒ√∛∜⊥∠∡∢∣∥∦'
        r'∞∯∰′″‴‵‶‷‸'
        r'ℓ℘ℜ℮ℱℒ'
        r'←↑→↓↔↕↖↗↘↙'
        r'⇐⇑⇒⇓⇔⇕⇖⇗⇘⇙⇚⇛⇜⇝⇞⇟'
        r'⇠⇡⇢⇣⇤⇥⇦⇧⇨⇩⇪'
        r'⊢⊣⊤⊥⊦⊧⊨⊩⊪⊫⊬⊭⊮⊯'
        r'⊰⊱⊲⊳⊴⊵⊶⊷⊸⊹⊺⊻⊼⊽⊾⊿'
        r'∁∂∃∄∅]'
    )

    def _build_page_hybrid_chapters(self, pdf_doc, page_count, book, style,
                                      spine, toc, options):
        """Page-level hybrid: text pages use text, formula/diagram pages use images.

        Strategy: pages with < 80 chars extracted text are likely diagrams or
        formula-only pages — render them as images. Other pages use text extraction.
        Much simpler and more robust than block-level classification.
        """
        dpi = options.get("dpi", self.IMAGE_DPI)
        min_text_chars = options.get("min_text_chars", 80)
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        text_pages = 0
        image_pages = 0

        for pn in range(page_count):
            page = pdf_doc[pn]
            text = page.get_text().strip()
            text_len = len(text)

            if text_len < min_text_chars:
                # Formula/diagram/title page — render as image
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                img_name = f"page_{pn:04d}.png"

                epub_img = epub.EpubImage()
                epub_img.file_name = f"images/{img_name}"
                epub_img.media_type = "image/png"
                epub_img.content = img_data
                book.add_item(epub_img)

                ch = epub.EpubHtml(
                    title=f"Page {pn+1}",
                    file_name=f"chap_{pn+1:03d}.xhtml", lang="zh-CN",
                )
                ch.content = (
                    f'<div class="page">'
                    f'<img src="images/{img_name}" alt="Page {pn+1}"/>'
                    f'</div>'
                )
                image_pages += 1
            else:
                # Text page — use structured rendering with paragraph merging
                page_html = self._render_page_as_html(page)
                if page_html is None:
                    # Fallback: render as image
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")
                    img_name = f"page_{pn:04d}.png"
                    epub_img = epub.EpubImage()
                    epub_img.file_name = f"images/{img_name}"
                    epub_img.media_type = "image/png"
                    epub_img.content = img_data
                    book.add_item(epub_img)
                    ch = epub.EpubHtml(
                        title=f"Page {pn+1}",
                        file_name=f"chap_{pn+1:03d}.xhtml", lang="zh-CN",
                    )
                    ch.content = (
                        f'<div class="page">'
                        f'<img src="images/{img_name}" alt="Page {pn+1}"/>'
                        f'</div>'
                    )
                    image_pages += 1
                else:
                    ch = epub.EpubHtml(
                        title=f"Page {pn+1}",
                        file_name=f"chap_{pn+1:03d}.xhtml", lang="zh-CN",
                    )
                    ch.content = page_html
                    text_pages += 1

            ch.add_item(style)
            book.add_item(ch)
            spine.append(ch)
            toc.append(
                epub.Link(f"chap_{pn+1:03d}.xhtml", f"Page {pn+1}", f"ch{pn+1}")
            )

            if (pn + 1) % 50 == 0:
                print(f"  Page {pn+1}/{page_count}: {text_pages} text, "
                      f"{image_pages} image")

        print(f"  Page hybrid done: {text_pages} text pages, "
              f"{image_pages} image pages")

    def _build_hybrid_text_image_chapters(self, pdf_doc, page_count, book, style,
                                           spine, toc, options):
        """Build EPUB with text for body and cropped images for math regions.

        Uses PyMuPDF's built-in text block detection with font analysis — NO
        external OCR dependency. Each text block is classified as "text" or
        "formula" based on font name, character content, and block geometry.
        """
        import re as _re
        import io as _io
        from PIL import Image as _Image

        dpi = options.get("dpi", 200)
        math_ratio_threshold = options.get("math_ratio", 0.1)
        mat = fitz.Matrix(dpi / 72, dpi / 72)

        # Compile regex patterns
        _math_char_re = _re.compile(self._MATH_CHAR_PATTERN)
        _math_font_re = _re.compile(
            '|'.join(self._MATH_FONT_PATTERNS), _re.IGNORECASE,
        )
        _text_char_re = _re.compile(r'[一-鿿　-〿＀-￯a-zA-Z0-9]')

        img_counter = 0
        total_math_blocks = 0

        for pn in range(page_count):
            page = pdf_doc[pn]
            text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            blocks = text_dict.get("blocks", [])

            if not blocks:
                continue

            # Render full page for cropping formula regions
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")

            html_parts = []

            for block in blocks:
                if block.get("type") != 0:  # image block
                    bbox = block["bbox"]
                    crop_data = self._crop_image_region(
                        img_bytes, pix.width, pix.height,
                        bbox[0] * dpi / 72, bbox[1] * dpi / 72,
                        bbox[2] * dpi / 72, bbox[3] * dpi / 72,
                    )
                    if crop_data:
                        img_counter += 1
                        img_name = f"img_{img_counter:05d}.png"
                        epub_img = epub.EpubImage()
                        epub_img.file_name = f"images/{img_name}"
                        epub_img.media_type = "image/png"
                        epub_img.content = crop_data
                        book.add_item(epub_img)
                        html_parts.append(
                            f'<div class="formula">'
                            f'<img src="images/{img_name}" alt="image"/>'
                            f'</div>'
                        )
                    total_math_blocks += 1
                    continue

                lines = block.get("lines", [])
                if not lines:
                    continue

                # Collect all spans in this block
                block_text_parts = []
                block_is_math = False
                block_font_info = []

                for line in lines:
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        font = span.get("font", "")
                        size = span.get("size", 0)
                        block_text_parts.append(text)
                        block_font_info.append((font, size, text))

                full_text = " ".join(block_text_parts)
                if not full_text:
                    continue

                # ---- classify block ----
                is_math = self._classify_as_math(
                    full_text, block_font_info, _math_char_re, _math_font_re,
                    _text_char_re, math_ratio_threshold,
                )

                if is_math:
                    # Crop formula region from page image
                    bbox = block["bbox"]
                    crop_data = self._crop_image_region(
                        img_bytes, pix.width, pix.height,
                        bbox[0] * dpi / 72, bbox[1] * dpi / 72,
                        bbox[2] * dpi / 72, bbox[3] * dpi / 72,
                    )
                    if crop_data:
                        img_counter += 1
                        img_name = f"img_{img_counter:05d}.png"
                        epub_img = epub.EpubImage()
                        epub_img.file_name = f"images/{img_name}"
                        epub_img.media_type = "image/png"
                        epub_img.content = crop_data
                        book.add_item(epub_img)
                        html_parts.append(
                            f'<div class="formula">'
                            f'<img src="images/{img_name}" alt="formula"/>'
                            f'</div>'
                        )
                    total_math_blocks += 1
                else:
                    # Text → HTML paragraph
                    escaped = full_text.replace(
                        "&", "&amp;"
                    ).replace("<", "&lt;").replace(">", "&gt;")
                    html_parts.append(f"<p>{escaped}</p>")

            if not html_parts:
                continue

            ch = epub.EpubHtml(
                title=f"Page {pn+1}",
                file_name=f"chap_{pn+1:03d}.xhtml", lang="zh-CN",
            )
            ch.content = "\n".join(html_parts)
            ch.add_item(style)
            book.add_item(ch)
            spine.append(ch)
            toc.append(
                epub.Link(f"chap_{pn+1:03d}.xhtml", f"Page {pn+1}", f"ch{pn+1}")
            )

            if (pn + 1) % 25 == 0:
                print(f"  Page {pn+1}/{page_count}, {total_math_blocks} math blocks, "
                      f"{img_counter} images")

        print(f"  Hybrid done: {total_math_blocks} formula blocks → "
              f"{img_counter} images embedded.")

    # ------------------------------------------------------------------
    # Block classification heuristics
    # ------------------------------------------------------------------

    def _classify_as_math(self, text, font_info, math_char_re, math_font_re,
                           text_char_re, threshold):
        """Classify a text block as math based primarily on font name.

        Math formulas in typeset PDFs almost always use distinct fonts
        (CMMI, CMSY, etc.). Character-based heuristics are unreliable
        because they confuse common symbols (=, +, -, etc.) with formulas.
        """
        if not text:
            return False

        # PRIMARY signal: math-specific font
        for font, _, _ in font_info:
            if math_font_re.search(font):
                return True

        # BACKUP: very short text with >=3 math-specific symbols
        # (only symbols like ∫∑∏√∞∂∇, NOT common operators)
        text_len = len(text.strip())
        if text_len < 25:
            math_chars = len(math_char_re.findall(text))
            if math_chars >= 3:
                return True

        return False

    # ------------------------------------------------------------------
    # Image cropping helper
    # ------------------------------------------------------------------

    @staticmethod
    def _crop_image_region(img_bytes, img_w, img_h, x1, y1, x2, y2):
        """Crop a region from a PNG image, with bounds checking and padding."""
        import io as _io
        from PIL import Image as _Image

        pad = 2
        x1 = max(0, int(x1) - pad)
        y1 = max(0, int(y1) - pad)
        x2 = min(img_w, int(x2) + pad)
        y2 = min(img_h, int(y2) + pad)

        if x2 <= x1 or y2 <= y1:
            return None

        try:
            img = _Image.open(_io.BytesIO(img_bytes))
            crop = img.crop((x1, y1, x2, y2))
            buf = _io.BytesIO()
            crop.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            return None
