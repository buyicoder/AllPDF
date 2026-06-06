# allpdf/models.py
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class FileFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"

    @classmethod
    def from_path(cls, path: Path) -> "FileFormat":
        suffix = path.suffix.lower().lstrip(".")
        mapping = {
            "pdf": cls.PDF,
            "docx": cls.DOCX,
            "doc": cls.DOCX,
            "xlsx": cls.XLSX,
            "xls": cls.XLSX,
            "pptx": cls.PPTX,
            "ppt": cls.PPTX,
        }
        if suffix not in mapping:
            raise ValueError(f"Unsupported format: .{suffix}")
        return mapping[suffix]

    def is_office_format(self) -> bool:
        return self in (FileFormat.DOCX, FileFormat.XLSX, FileFormat.PPTX)

    def is_pdf(self) -> bool:
        return self == FileFormat.PDF


class ConversionStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class QualityGrade(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class FileInfo(BaseModel):
    path: Path
    format: FileFormat
    page_count: int = 0
    image_count: int = 0
    table_count: int = 0
    is_scanned: bool = False
    file_size_bytes: int = 0


class QualityCheckItem(BaseModel):
    name: str
    grade: QualityGrade
    detail: str


class QualityReport(BaseModel):
    overall_grade: QualityGrade
    checks: list[QualityCheckItem] = Field(default_factory=list)
    summary: str = ""

    @classmethod
    def from_checks(cls, checks: list[QualityCheckItem]) -> "QualityReport":
        if any(c.grade == QualityGrade.RED for c in checks):
            overall = QualityGrade.RED
        elif any(c.grade == QualityGrade.YELLOW for c in checks):
            overall = QualityGrade.YELLOW
        else:
            overall = QualityGrade.GREEN

        detail_lines = [f"{'✓' if c.grade == QualityGrade.GREEN else '⚠' if c.grade == QualityGrade.YELLOW else '✗'} {c.name}: {c.detail}" for c in checks]
        return cls(
            overall_grade=overall,
            checks=checks,
            summary="\n".join(detail_lines),
        )


class ConversionResult(BaseModel):
    input_path: Path
    output_path: Path
    input_format: FileFormat
    output_format: FileFormat
    status: ConversionStatus
    engine_used: str
    duration_seconds: float
    quality_report: Optional[QualityReport] = None
    retries: int = 0
    error_message: Optional[str] = None
