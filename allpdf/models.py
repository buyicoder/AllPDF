"""Data models for AllPDF — conversion tasks, quality reports, and file metadata.

All models use Pydantic for validation and serialization. Enums inherit from
``(str, Enum)`` for transparent JSON compatibility.
"""

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class FileFormat(str, Enum):
    """Supported file formats for conversion.

    Maps legacy extensions (``.doc``, ``.xls``, ``.ppt``) to their modern
    equivalents (``.docx``, ``.xlsx``, ``.pptx``).
    """

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    EPUB = "epub"

    @classmethod
    def from_path(cls, path: Path) -> "FileFormat":
        """Detect file format from a path's extension.

        Args:
            path: File path with an extension.

        Returns:
            The detected ``FileFormat``.

        Raises:
            ValueError: If the extension is not a supported format.
        """
        suffix = path.suffix.lower().lstrip(".")
        mapping = {
            "pdf": cls.PDF,
            "docx": cls.DOCX,
            "doc": cls.DOCX,
            "xlsx": cls.XLSX,
            "xls": cls.XLSX,
            "pptx": cls.PPTX,
            "ppt": cls.PPTX,
            "epub": cls.EPUB,
        }
        if suffix not in mapping:
            raise ValueError(f"Unsupported format: .{suffix}")
        return mapping[suffix]

    def is_office_format(self) -> bool:
        """Return True for Word, Excel, and PowerPoint formats."""
        return self in (FileFormat.DOCX, FileFormat.XLSX, FileFormat.PPTX)

    def is_pdf(self) -> bool:
        """Return True if this format is PDF."""
        return self == FileFormat.PDF


class ConversionStatus(str, Enum):
    """Terminal status of a conversion task."""

    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class QualityGrade(str, Enum):
    """Traffic-light grade for quality check results.

    RED means the check failed and the result should not be used.
    YELLOW means a warning — the result is usable but may have issues.
    GREEN means the check passed.
    """

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class FileInfo(BaseModel):
    """Metadata about a file, gathered before or after conversion.

    Used by the orchestrator for engine selection and by the quality
    checker for before/after comparison.
    """

    path: Path
    format: FileFormat
    page_count: int = 0
    image_count: int = 0
    table_count: int = 0
    is_scanned: bool = False
    file_size_bytes: int = 0


class QualityCheckItem(BaseModel):
    """A single quality check result (e.g., page count, image count)."""

    name: str
    grade: QualityGrade
    detail: str


class QualityReport(BaseModel):
    """Aggregate quality report for a conversion result.

    The ``from_checks`` factory method is the recommended way to create
    a report — it derives the overall grade from individual check grades
    using the rule: RED if any check is RED, YELLOW if any is YELLOW
    (and no REDs), GREEN otherwise.
    """

    overall_grade: QualityGrade
    checks: list[QualityCheckItem] = Field(default_factory=list)
    summary: str = ""

    @classmethod
    def from_checks(cls, checks: list[QualityCheckItem]) -> "QualityReport":
        """Create a QualityReport from a list of individual checks.

        Derives ``overall_grade`` from checks: RED > YELLOW > GREEN.
        Auto-generates ``summary`` as a newline-separated list of check results.
        """
        if any(c.grade == QualityGrade.RED for c in checks):
            overall = QualityGrade.RED
        elif any(c.grade == QualityGrade.YELLOW for c in checks):
            overall = QualityGrade.YELLOW
        else:
            overall = QualityGrade.GREEN

        detail_lines = [
            f"{'✓' if c.grade == QualityGrade.GREEN else '⚠' if c.grade == QualityGrade.YELLOW else '✗'} {c.name}: {c.detail}"
            for c in checks
        ]
        return cls(
            overall_grade=overall,
            checks=checks,
            summary="\n".join(detail_lines),
        )


class ConversionResult(BaseModel):
    """The result of a single conversion attempt.

    Includes the engine used, timing, optional quality report, and
    retry count. When ``status`` is FAILED, ``error_message`` contains
    a human-readable explanation.
    """

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
