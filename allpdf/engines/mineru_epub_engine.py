"""PDF to EPUB engine using MinerU cloud API for high-quality extraction.

MinerU (by OpenDataLab/Shanghai AI Lab) provides state-of-the-art PDF
extraction with excellent support for Chinese text, mathematical formulas,
complex tables, and multi-column layouts.

Pipeline: PDF → MinerU cloud API → Markdown + Images → ebooklib → EPUB

Supports two modes:
- Flash (default): free, no token, fast, up to 10MB/20 pages
- Precision: requires free API token from https://mineru.net, higher quality
"""
import os
import re
import tempfile
import time
from pathlib import Path

from ebooklib import epub

from allpdf.engines.base import ConversionEngine
from allpdf.models import ConversionResult, ConversionStatus, FileFormat


class MinerUEpubEngine(ConversionEngine):
    """Convert PDF to EPUB using MinerU cloud API.

    Handles:
    - Text with proper paragraph/heading structure
    - LaTeX formulas (embedded as code spans for readability)
    - HTML tables (preserved from MinerU output)
    - Images (embedded as proper EPUB assets)
    - Chinese and 100+ languages
    """

    name = "mineru-epub"
    input_format = FileFormat.PDF
    output_format = FileFormat.EPUB

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(self, input_path: str, output_path: str, **options) -> ConversionResult:
        start = time.time()

        if not os.path.exists(input_path):
            return ConversionResult(
                input_path=Path(input_path), output_path=Path(output_path),
                input_format=FileFormat.PDF, output_format=FileFormat.EPUB,
                status=ConversionStatus.FAILED, engine_used=self.name,
                duration_seconds=time.time() - start,
                error_message=f"Input file not found: {input_path}",
            )

        token = options.get("mineru_token") or os.environ.get("MINERU_TOKEN")
        use_precision = options.get("precision", bool(token))
        language = options.get("language", "ch")

        try:
            from mineru import MinerU

            client = MinerU(token) if use_precision and token else MinerU()
            mode = "precision" if (use_precision and token) else "flash"
            print(f"  MinerU mode: {mode}, language: {language}")

            # ---- step 1: extract with MinerU ----
            print(f"  Extracting PDF content via MinerU...")
            if mode == "flash":
                result = client.flash_extract(
                    input_path,
                    language=language,
                    is_ocr=options.get("ocr", True),
                    enable_formula=options.get("formula", True),
                    enable_table=options.get("table", True),
                    timeout=options.get("timeout", 600),
                )
            else:
                result = client.extract(
                    input_path,
                    ocr=options.get("ocr", True),
                    formula=options.get("formula", True),
                    table=options.get("table", True),
                    language=language,
                    timeout=options.get("timeout", 600),
                )

            if not result.markdown:
                return ConversionResult(
                    input_path=Path(input_path), output_path=Path(output_path),
                    input_format=FileFormat.PDF, output_format=FileFormat.EPUB,
                    status=ConversionStatus.FAILED, engine_used=self.name,
                    duration_seconds=time.time() - start,
                    error_message="MinerU returned empty markdown content",
                )

            print(f"  Got {len(result.markdown):,} chars markdown, {len(result.images)} images")

            # ---- step 2: build EPUB from markdown + images ----
            self._build_epub(
                markdown=result.markdown,
                images=result.images,
                output_path=output_path,
                title=Path(input_path).stem,
                options=options,
            )

            duration = time.time() - start
            out_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            print(f"  EPUB: {out_size/1024/1024:.1f} MB in {duration:.0f}s")

            return ConversionResult(
                input_path=Path(input_path), output_path=Path(output_path),
                input_format=FileFormat.PDF, output_format=FileFormat.EPUB,
                status=ConversionStatus.SUCCESS, engine_used=self.name,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = time.time() - start
            import traceback
            traceback.print_exc()
            return ConversionResult(
                input_path=Path(input_path), output_path=Path(output_path),
                input_format=FileFormat.PDF, output_format=FileFormat.EPUB,
                status=ConversionStatus.FAILED, engine_used=self.name,
                duration_seconds=duration,
                error_message=f"{type(e).__name__}: {e}",
            )

    # ------------------------------------------------------------------
    # EPUB building
    # ------------------------------------------------------------------

    def _build_epub(self, markdown: str, images: list, output_path: str,
                    title: str, options: dict):
        """Build an EPUB from MinerU markdown + images."""
        book = epub.EpubBook()
        book.set_identifier(f"allpdf-mineru-{int(time.time())}")
        book.set_title(title)
        book.set_language(options.get("epub_language", "zh-CN"))
        book.add_author("Converted by AllPDF + MinerU")

        # CSS
        style_content = (
            "body{font-family:serif;font-size:1em;line-height:1.8;margin:0.5em}"
            "h1,h2,h3,h4{margin-top:1em;margin-bottom:0.5em}"
            "p{margin:0.5em 0;text-indent:0}"
            "img{max-width:100%;height:auto;display:block;margin:0.5em auto}"
            "table{border-collapse:collapse;width:100%;margin:0.5em 0;font-size:0.85em}"
            "td,th{border:1px solid #999;padding:0.3em 0.5em}"
            "th{background:#eee}"
            "pre,code.math,code.latex{font-family:monospace;background:#f5f5f5}"
            "code.math,code.latex{white-space:normal}"
            "pre.math,pre.latex{padding:0.5em;overflow-x:auto}"
            "blockquote{margin:0.5em 1em;padding-left:0.5em;border-left:3px solid #ccc;color:#555}"
        )
        css_item = epub.EpubItem(
            uid="style", file_name="style/default.css",
            media_type="text/css", content=style_content,
        )
        book.add_item(css_item)

        # Add images as EPUB assets
        image_map = {}  # original path → epub file_name
        for i, img in enumerate(images):
            epub_img = epub.EpubImage()
            epub_img.file_name = f"images/{img.name}"
            epub_img.media_type = self._guess_media_type(img.name)
            epub_img.content = img.data
            book.add_item(epub_img)
            # Map various possible reference paths
            image_map[img.name] = f"images/{img.name}"
            image_map[f"images/{img.name}"] = f"images/{img.name}"
            image_map[img.path] = f"images/{img.name}" if img.path else f"images/{img.name}"

        # Convert markdown to HTML, split into chapters at headings
        html_body = self._markdown_to_html(markdown, image_map)
        chapters = self._split_into_chapters(html_body)

        spine = ["nav"]
        toc = []

        for idx, (chap_title, chap_html) in enumerate(chapters):
            cn = idx + 1
            file_name = f"chap_{cn:03d}.xhtml"
            ch = epub.EpubHtml(
                title=chap_title or f"Chapter {cn}",
                file_name=file_name,
                lang=options.get("epub_language", "zh-CN"),
            )
            ch.content = chap_html
            ch.add_item(css_item)
            book.add_item(ch)
            spine.append(ch)
            toc.append(epub.Link(file_name, chap_title or f"Chapter {cn}", f"ch{cn}"))

        book.toc = toc
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = spine

        epub.write_epub(output_path, book)

    # ------------------------------------------------------------------
    # Markdown → HTML
    # ------------------------------------------------------------------

    # Regex patterns for LaTeX math (protect before markdown processing)
    _MATH_BLOCK = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)
    _MATH_INLINE = re.compile(r'\$(.+?)\$')
    _IMG_MD = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    _IMG_HTML = re.compile(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)

    def _markdown_to_html(self, md: str, image_map: dict[str, str]) -> str:
        """Convert MinerU markdown to HTML suitable for EPUB.

        Handles:
        - Standard markdown via ``markdown`` library
        - LaTeX math ($...$ and $$...$$) → <code>/<pre> tags
        - Image path rewriting to EPUB image paths
        - HTML table passthrough (MinerU outputs HTML tables)
        """
        import markdown as md_lib

        # Step 1: protect LaTeX formulas from markdown processing
        latex_blocks = {}
        latex_counter = [0]

        def _save_block(m):
            key = f"LATEXBLOCK{latex_counter[0]}"
            latex_blocks[key] = m.group(0)
            latex_counter[0] += 1
            return key

        def _save_inline(m):
            key = f"LATEXINLINE{latex_counter[0]}"
            latex_blocks[key] = m.group(0)
            latex_counter[0] += 1
            return key

        md = self._MATH_BLOCK.sub(_save_block, md)
        md = self._MATH_INLINE.sub(_save_inline, md)

        # Step 2: fix image paths in markdown ![alt](path)
        def _fix_md_img(m):
            alt = m.group(1)
            src = m.group(2)
            new_src = image_map.get(src, image_map.get(os.path.basename(src), src))
            return f'![{alt}]({new_src})'

        md = self._IMG_MD.sub(_fix_md_img, md)

        # Step 3: convert markdown to HTML
        html = md_lib.markdown(
            md,
            extensions=['tables', 'fenced_code', 'codehilite', 'nl2br'],
            output_format='html',
        )

        # Step 4: fix image paths in HTML <img> tags
        def _fix_html_img(m):
            src = m.group(1)
            new_src = image_map.get(src, image_map.get(os.path.basename(src), src))
            return m.group(0).replace(f'src="{src}"', f'src="{new_src}"').replace(
                f"src='{src}'", f"src='{new_src}'"
            )

        html = self._IMG_HTML.sub(_fix_html_img, html)

        # Step 5: restore LaTeX formulas as styled HTML
        for key, value in latex_blocks.items():
            if value.startswith("$$"):
                inner = value[2:-2].strip()
                escaped = inner.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                replacement = f'<pre class="math latex">{escaped}</pre>'
            else:
                inner = value[1:-1].strip()
                escaped = inner.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                replacement = f'<code class="math latex">{escaped}</code>'
            html = html.replace(key, replacement)

        return html

    # ------------------------------------------------------------------
    # Chapter splitting
    # ------------------------------------------------------------------

    _HEADING = re.compile(r'<h([12])[^>]*>(.*?)</h\1>', re.IGNORECASE)

    def _split_into_chapters(self, html: str) -> list[tuple[str, str]]:
        """Split HTML body at H1/H2 headings into chapters.

        Returns:
            List of (chapter_title, chapter_html_body) tuples.
        """
        # Find all heading positions
        headings = list(self._HEADING.finditer(html))
        if not headings:
            # No headings — single chapter
            title = self._extract_title(html)
            return [(title, f"<html><body>{html}</body></html>")]

        chapters = []
        for i, m in enumerate(headings):
            start = m.start()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(html)
            level = m.group(1)
            title = self._strip_tags(m.group(2))
            # Build HTML for this chapter: include the heading + content
            chap_html = f"<html><body>\n<h{level}>{title}</h{level}>\n{html[start + len(m.group(0)):end]}\n</body></html>"
            chapters.append((title, chap_html))

        return chapters

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_title(self, html: str, max_len: int = 50) -> str:
        """Extract a title from the first heading or first text."""
        m = re.search(r'<h[1-3][^>]*>(.*?)</h[1-3]>', html, re.IGNORECASE)
        if m:
            return self._strip_tags(m.group(1))[:max_len]
        # Fallback: first paragraph
        m = re.search(r'<p[^>]*>(.*?)</p>', html, re.IGNORECASE)
        if m:
            return self._strip_tags(m.group(1))[:max_len]
        return "Chapter 1"

    @staticmethod
    def _strip_tags(text: str) -> str:
        """Remove HTML tags from text."""
        return re.sub(r'<[^>]+>', '', text).strip()

    @staticmethod
    def _guess_media_type(filename: str) -> str:
        """Guess MIME type from filename."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mapping = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "svg": "image/svg+xml",
            "webp": "image/webp",
            "bmp": "image/bmp",
        }
        return mapping.get(ext, "image/png")
