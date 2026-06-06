"""Convert PDF to EPUB using MinerU cloud API for high-quality extraction.

MinerU excels at:
- Chinese text recognition (109 languages supported)
- Mathematical formula extraction (LaTeX output)
- Complex table parsing (HTML tables preserved)
- Multi-column / complex layout handling

Modes:
- Flash (default): free, no API token needed, up to 10MB / 20 pages
- Precision: free token from https://mineru.net, up to 200MB / 200 pages

Usage:
    python convert_mineru.py book.pdf
    python convert_mineru.py book.pdf -o output.epub
    python convert_mineru.py book.pdf --precision --token YOUR_TOKEN
    python convert_mineru.py book.pdf --language en

Environment variable:
    MINERU_TOKEN — API token for precision mode (or use --token)
"""
import os
import sys
import time

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from allpdf.engines.mineru_epub_engine import MinerUEpubEngine


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert PDF to EPUB using MinerU (high-quality AI extraction)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="Path to input PDF file")
    parser.add_argument("-o", "--output", default=None, help="Path to output EPUB file")
    parser.add_argument("--token", default=None, help="MinerU API token (or set MINERU_TOKEN env)")
    parser.add_argument("--precision", action="store_true", help="Use precision mode (higher quality)")
    parser.add_argument("--language", default="ch", help="Document language code (default: ch)")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR")
    parser.add_argument("--no-formula", action="store_true", help="Disable formula recognition")
    parser.add_argument("--no-table", action="store_true", help="Disable table recognition")
    parser.add_argument("--timeout", type=int, default=600, help="API timeout in seconds (default: 600)")
    parser.add_argument("--epub-language", default="zh-CN", help="EPUB metadata language (default: zh-CN)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    output = args.output
    if output is None:
        from pathlib import Path
        output = str(Path(args.input).with_suffix(".epub"))

    # Remove existing output
    if os.path.exists(output):
        os.remove(output)

    token = args.token or os.environ.get("MINERU_TOKEN")

    engine = MinerUEpubEngine()
    print(f"Source: {args.input} ({os.path.getsize(args.input)/1024/1024:.1f} MB)")
    print(f"Output: {output}")
    print(f"Mode: {'precision' if (args.precision and token) else 'flash'}")

    t0 = time.time()
    result = engine.convert(
        args.input,
        output,
        mineru_token=token,
        precision=args.precision,
        language=args.language,
        ocr=not args.no_ocr,
        formula=not args.no_formula,
        table=not args.no_table,
        timeout=args.timeout,
        epub_language=args.epub_language,
    )

    elapsed = time.time() - t0

    if result.status.value == "success":
        sz = os.path.getsize(output) if os.path.exists(output) else 0
        print(f"\nDone: {elapsed:.0f}s → {output} ({sz/1024/1024:.1f} MB)")

        # Show EPUB structure
        from zipfile import ZipFile
        with ZipFile(output) as z:
            names = z.namelist()
            imgs = [n for n in names if n.startswith("EPUB/images/")]
            chaps = [n for n in names if n.startswith("EPUB/chap_")]
            print(f"Chapters: {len(chaps)}, Images: {len(imgs)}")

            if chaps:
                first_chap = sorted(chaps)[0]
                html = z.read(first_chap).decode("utf-8")
                # Show a preview
                preview = html[:600].replace("\n", " ")
                print(f"\nFirst chapter preview ({len(html)} chars):")
                print(preview)
    else:
        print(f"\nFailed: {result.error_message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
