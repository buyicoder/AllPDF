# allpdf/mcp/tools.py
"""MCP tool definitions for AllPDF."""
import os
from pathlib import Path
from allpdf.orchestrator import Orchestrator
from allpdf.models import FileFormat
from allpdf.quality.compare import compare

_orchestrator = Orchestrator()


def convert_file(input_path, output_path, input_format=None, output_format=None,
                 quality_check=True, retry=2):
    """Convert a file with quality checks. AI mode: full orchestration chain."""
    src_fmt = FileFormat(input_format) if input_format else None
    dst_fmt = FileFormat(output_format) if output_format else None

    result = _orchestrator.convert(
        input_path, output_path, input_format=src_fmt, output_format=dst_fmt,
        quality_check=quality_check, retry=retry,
    )

    response = {
        "status": result.status.value,
        "input": str(result.input_path),
        "output": str(result.output_path),
        "input_format": result.input_format.value,
        "output_format": result.output_format.value,
        "engine": result.engine_used,
        "duration_seconds": round(result.duration_seconds, 2),
        "retries": result.retries,
    }
    if result.error_message:
        response["error"] = result.error_message
    if result.quality_report:
        response["quality"] = {
            "overall": result.quality_report.overall_grade.value,
            "checks": [{"name": c.name, "grade": c.grade.value, "detail": c.detail}
                       for c in result.quality_report.checks],
            "summary": result.quality_report.summary,
        }
    return response


def analyze_file(filepath):
    """Analyze a file — returns format, pages, images, scanned status."""
    from allpdf.engines.pymupdf_ops import PyMuPDFOps
    from allpdf.utils import detect_format

    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    fmt = detect_format(Path(filepath))
    info = {"path": filepath, "format": fmt.value, "file_size_bytes": os.path.getsize(filepath)}

    if fmt == FileFormat.PDF:
        ops = PyMuPDFOps()
        result = ops.analyze(filepath)
        if result:
            info.update({
                "page_count": result.page_count,
                "image_count": result.image_count,
                "table_count": result.table_count,
                "is_scanned": result.is_scanned,
            })
    return info


def check_quality(source_path, result_path):
    """Compare source and result, return quality report."""
    if not os.path.exists(source_path):
        return {"error": f"Source not found: {source_path}"}
    if not os.path.exists(result_path):
        return {"error": f"Result not found: {result_path}"}

    report = compare(source_path, result_path)
    return {
        "overall": report.overall_grade.value,
        "checks": [{"name": c.name, "grade": c.grade.value, "detail": c.detail}
                   for c in report.checks],
        "summary": report.summary,
    }


def list_engines():
    """List all registered conversion engines."""
    return [{"name": e.name, "input_format": e.input_format.value,
             "output_format": e.output_format.value, "available": e.is_available()}
            for e in _orchestrator.list_engines()]


def get_supported_formats():
    """Return the complete conversion matrix."""
    return _orchestrator.get_supported_conversions()
