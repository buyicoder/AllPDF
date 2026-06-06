# allpdf/quality/compare.py
"""Side-by-side comparison of source and result files."""
from pathlib import Path
from allpdf.models import FileFormat
from allpdf.quality.checker import QualityChecker


def compare(input_path: str, output_path: str) -> "QualityReport":
    """Compare a source file and its conversion result."""
    from allpdf.models import QualityReport
    checker = QualityChecker()
    input_fmt = FileFormat.from_path(Path(input_path))
    output_fmt = FileFormat.from_path(Path(output_path))
    return checker.run(input_path, output_path, input_fmt, output_fmt)
