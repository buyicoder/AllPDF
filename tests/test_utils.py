# tests/test_utils.py
import tempfile
from pathlib import Path
from allpdf.utils import (
    temp_output_path, detect_format, ensure_dir,
    count_pdf_pages, count_pdf_images,
)
from allpdf.models import FileFormat


class TestTempOutputPath:
    def test_pdf_to_docx_same_name(self):
        result = temp_output_path("docs/report.pdf", "docx")
        assert result.endswith("_converted.docx")
        assert "report" in result

    def test_docx_to_pdf(self):
        result = temp_output_path("letter.docx", "pdf")
        assert result.endswith("_converted.pdf")


class TestDetectFormat:
    def test_detect_pdf(self):
        assert detect_format(Path("file.pdf")) == FileFormat.PDF

    def test_detect_docx(self):
        assert detect_format(Path("file.docx")) == FileFormat.DOCX

    def test_detect_xlsx(self):
        assert detect_format(Path("file.xlsx")) == FileFormat.XLSX

    def test_detect_pptx(self):
        assert detect_format(Path("file.pptx")) == FileFormat.PPTX

    def test_detect_unknown_raises(self):
        import pytest
        with pytest.raises(ValueError):
            detect_format(Path("file.xyz"))


class TestEnsureDir:
    def test_creates_directory(self, tmp_path):
        d = tmp_path / "sub" / "nested"
        result = ensure_dir(str(d))
        assert result.exists()
        assert result.is_dir()


class TestCountPdfPages:
    def test_counts_pages(self):
        import fitz
        doc = fitz.open()
        doc.new_page()
        doc.new_page()
        doc.new_page()
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        doc.save(tmp.name)
        doc.close()

        count = count_pdf_pages(tmp.name)
        assert count == 3

        Path(tmp.name).unlink()
