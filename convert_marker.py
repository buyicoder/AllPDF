"""Convert scanned PDF to EPUB using Marker OCR."""
import sys, os, time, multiprocessing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn", force=True)

    src = r"D:\Books\线性代数 (第6版) (（美）吉尔伯特·斯特朗) (z-library.sk, 1lib.sk, z-lib.sk).pdf"
    out_dir = r"D:\Books\线性代数_marker"

    print("Loading Marker models...")
    t0 = time.time()
    converter = PdfConverter(
        artifact_dict=create_model_dict(),
    )
    print(f"Models loaded in {time.time()-t0:.0f}s")

    print(f"Converting {src}...")
    t0 = time.time()
    rendered = converter(src)
    elapsed = time.time() - t0
    print(f"Done in {elapsed:.0f}s")

    # Save markdown
    md_path = os.path.join(out_dir, "output.md")
    os.makedirs(out_dir, exist_ok=True)
    markdown, _, _ = text_from_rendered(rendered)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"Markdown saved: {md_path} ({len(markdown):,} chars)")
