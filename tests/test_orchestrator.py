# tests/test_orchestrator.py
import os
from pathlib import Path
import fitz
from allpdf.orchestrator import Orchestrator
from allpdf.models import FileFormat


def _make_pdf(path: str, pages: int = 1):
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i+1} content for testing", fontsize=12)
    doc.save(path)
    doc.close()


class TestOrchestrator:
    def test_convert_pdf_to_docx(self, tmp_path):
        pdf = tmp_path / "input.pdf"
        _make_pdf(str(pdf))

        out = tmp_path / "output.docx"
        orch = Orchestrator()
        result = orch.convert(str(pdf), str(out), FileFormat.PDF, FileFormat.DOCX)

        assert result.status.value == "success"
        assert os.path.exists(str(out))

    def test_convert_with_auto_detect_format(self, tmp_path):
        pdf = tmp_path / "input.pdf"
        _make_pdf(str(pdf))

        out = tmp_path / "output.docx"
        orch = Orchestrator()
        result = orch.convert_auto(str(pdf), str(out), FileFormat.DOCX)

        assert result.status.value == "success"

    def test_unsupported_conversion_returns_failed(self, tmp_path):
        orch = Orchestrator()
        result = orch.convert(
            str(tmp_path / "x.txt"), str(tmp_path / "x.docx"),
            FileFormat.PDF, FileFormat.DOCX,
        )
        assert result.status.value == "failed"

    def test_list_available_engines(self):
        orch = Orchestrator()
        engines = orch.list_engines()
        assert len(engines) > 0
        for e in engines:
            assert e.name
            assert isinstance(e.is_available(), bool)

    def test_quality_check_option(self, tmp_path):
        pdf = tmp_path / "input.pdf"
        _make_pdf(str(pdf))

        out = tmp_path / "output.docx"
        orch = Orchestrator()
        result = orch.convert(
            str(pdf), str(out), FileFormat.PDF, FileFormat.DOCX,
            quality_check=True,
        )

        assert result.quality_report is not None
