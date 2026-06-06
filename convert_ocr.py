"""One-off: convert scanned PDF to EPUB with OCR hybrid (text + formula images)."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from allpdf.engines.pdf2epub_engine import Pdf2EpubEngine

src = r"D:\Books\线性代数 (第6版) (（美）吉尔伯特·斯特朗) (z-library.sk, 1lib.sk, z-lib.sk).pdf"
out = r"D:\Books\线性代数 (第6版).epub"

if os.path.exists(out):
    os.remove(out)

print(f"Source: {os.path.getsize(src)/1024/1024:.0f} MB")
engine = Pdf2EpubEngine()
t0 = time.time()
result = engine.convert(src, out, ocr=True, dpi=120)
elapsed = time.time() - t0

if result.status.value == "success":
    sz = os.path.getsize(out)
    print(f"\nDone: {elapsed:.0f}s, {sz/1024/1024:.0f} MB")

    from zipfile import ZipFile
    with ZipFile(out) as z:
        names = z.namelist()
        imgs = [n for n in names if n.startswith('EPUB/images/')]
        chaps = [n for n in names if n.startswith('EPUB/chap_')]
        print(f"Chapters: {len(chaps)}, Formula images: {len(imgs)}")
        html = z.read('EPUB/chap_001.xhtml').decode('utf-8')
        print(f"\nChapter 1 ({len(html)} chars):")
        print(html[:800])
else:
    print(f"Failed: {result.error_message}")
