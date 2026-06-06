# allpdf/cli/convert.py
import os
import click
from allpdf.orchestrator import Orchestrator
from allpdf.models import FileFormat
from allpdf.quality.report import format_report


@click.command()
@click.argument("input_file")
@click.option("--to", "target_format", default=None, help="Target format (pdf, docx, xlsx, pptx, epub)")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--pages", default=None, help="Page range (e.g., 1-3,5,7)")
@click.option("--engine", default=None, help="Engine to use (e.g. mineru-epub for PDF→EPUB via MinerU)")
@click.option("--quality-check/--no-quality-check", default=False, help="Run quality checks after conversion")
@click.option("--retry", type=int, default=0, help="Retry count with alternative engines")
@click.option("--output-format", "out_fmt", type=click.Choice(["text", "json"]), default="text")
def convert(input_file, target_format, output, pages, engine, quality_check, retry, out_fmt):
    """Convert a file to another format."""
    if not os.path.exists(input_file):
        click.echo(f"Error: File not found: {input_file}", err=True)
        raise SystemExit(1)

    if target_format is None:
        from pathlib import Path
        src_fmt = FileFormat.from_path(Path(input_file))
        if src_fmt == FileFormat.PDF:
            click.echo("Error: PDF input requires --to target format", err=True)
            raise SystemExit(1)
        target_format = "pdf"

    dst_fmt = FileFormat(target_format)

    if output is None:
        from allpdf.utils import temp_output_path
        output = temp_output_path(input_file, target_format)

    page_list = _parse_pages(pages) if pages else None

    orch = Orchestrator()
    click.echo(f"Converting: {input_file} -> {output}")

    result = orch.convert_auto(
        input_file, output, dst_fmt,
        quality_check=quality_check, retry=retry, pages=page_list,
        engine=engine,
    )

    if result.status.value == "success":
        if out_fmt == "json":
            import json
            d = {
                "status": "success",
                "input": str(result.input_path),
                "output": str(result.output_path),
                "input_format": result.input_format.value,
                "output_format": result.output_format.value,
                "engine": result.engine_used,
                "duration": round(result.duration_seconds, 2),
                "retries": result.retries,
            }
            if result.quality_report:
                d["quality"] = {
                    "grade": result.quality_report.overall_grade.value,
                    "checks": [{"name": c.name, "grade": c.grade.value, "detail": c.detail}
                               for c in result.quality_report.checks],
                }
            click.echo(json.dumps(d, indent=2, ensure_ascii=False))
        else:
            click.echo(f"Done in {result.duration_seconds:.1f}s → {result.output_path}")
            if result.quality_report:
                click.echo(format_report(result.quality_report))
    else:
        if out_fmt == "json":
            import json
            click.echo(json.dumps({"status": "failed", "error": result.error_message, "engine": result.engine_used},
                                  indent=2, ensure_ascii=False))
        else:
            click.echo(f"Failed: {result.error_message}", err=True)
        raise SystemExit(1)


def _parse_pages(pages_str):
    if not pages_str:
        return None
    pages = []
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.extend(range(int(start) - 1, int(end)))
        else:
            pages.append(int(part) - 1)
    return pages
