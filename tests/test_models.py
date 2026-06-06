# tests/test_models.py
import pytest
from pathlib import Path
from allpdf.models import (
    FileFormat, ConversionStatus, QualityGrade,
    FileInfo, QualityCheckItem, QualityReport, ConversionResult
)


class TestFileFormat:
    def test_from_extension_pdf(self):
        assert FileFormat.from_path(Path("doc.pdf")) == FileFormat.PDF

    def test_from_extension_docx(self):
        assert FileFormat.from_path(Path("doc.docx")) == FileFormat.DOCX

    def test_from_extension_xlsx(self):
        assert FileFormat.from_path(Path("sheet.xlsx")) == FileFormat.XLSX

    def test_from_extension_pptx(self):
        assert FileFormat.from_path(Path("slides.pptx")) == FileFormat.PPTX

    def test_unknown_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported format"):
            FileFormat.from_path(Path("file.xyz"))


class TestFileInfo:
    def test_create_minimal(self):
        info = FileInfo(
            path=Path("doc.pdf"),
            format=FileFormat.PDF,
            page_count=3,
            image_count=1,
            table_count=0,
            is_scanned=False,
            file_size_bytes=12345,
        )
        assert info.page_count == 3
        assert info.format == FileFormat.PDF


class TestQualityReport:
    def test_overall_green_when_all_checks_green(self):
        checks = [
            QualityCheckItem(name="pages", grade=QualityGrade.GREEN, detail="3 pages, matches"),
            QualityCheckItem(name="images", grade=QualityGrade.GREEN, detail="1 image, matches"),
        ]
        report = QualityReport(overall_grade=QualityGrade.GREEN, checks=checks, summary="All good")
        assert report.overall_grade == QualityGrade.GREEN

    def test_overall_red_when_any_check_red(self):
        checks = [
            QualityCheckItem(name="pages", grade=QualityGrade.GREEN, detail="3 pages, matches"),
            QualityCheckItem(name="openable", grade=QualityGrade.RED, detail="Cannot open output file"),
        ]
        report = QualityReport(overall_grade=QualityGrade.RED, checks=checks, summary="Failed")
        assert report.overall_grade == QualityGrade.RED

    def test_overall_yellow_when_yellow_exists_no_red(self):
        checks = [
            QualityCheckItem(name="pages", grade=QualityGrade.GREEN, detail="ok"),
            QualityCheckItem(name="images", grade=QualityGrade.YELLOW, detail="mismatch"),
        ]
        report = QualityReport(overall_grade=QualityGrade.YELLOW, checks=checks, summary="Warnings")
        assert report.overall_grade == QualityGrade.YELLOW


class TestConversionResult:
    def test_success_result(self):
        result = ConversionResult(
            input_path=Path("in.pdf"),
            output_path=Path("out.docx"),
            input_format=FileFormat.PDF,
            output_format=FileFormat.DOCX,
            status=ConversionStatus.SUCCESS,
            engine_used="pdf2docx",
            duration_seconds=1.5,
            retries=0,
        )
        assert result.status == ConversionStatus.SUCCESS
        assert result.quality_report is None

    def test_failed_result_with_error(self):
        result = ConversionResult(
            input_path=Path("in.pdf"),
            output_path=Path("out.docx"),
            input_format=FileFormat.PDF,
            output_format=FileFormat.DOCX,
            status=ConversionStatus.FAILED,
            engine_used="pdf2docx",
            duration_seconds=5.0,
            retries=2,
            error_message="PDF is password protected",
        )
        assert result.status == ConversionStatus.FAILED
        assert "password" in result.error_message
