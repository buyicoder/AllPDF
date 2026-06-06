# allpdf/cli/check.py
import os
import click
from allpdf.quality.compare import compare
from allpdf.quality.report import format_report


@click.command()
@click.argument("source")
@click.argument("result")
@click.option("--compare/--no-compare", default=True, help="Compare source and result")
def check(source, result, compare_flag):
    """Check the quality of a conversion result."""
    if not os.path.exists(source):
        click.echo(f"Error: Source file not found: {source}", err=True)
        raise SystemExit(1)
    if not os.path.exists(result):
        click.echo(f"Error: Result file not found: {result}", err=True)
        raise SystemExit(1)

    if compare_flag:
        report = compare(source, result)
        click.echo(format_report(report, verbose=True))
    else:
        from allpdf.engines.pymupdf_ops import PyMuPDFOps
        ops = PyMuPDFOps()
        info = ops.analyze(result)
        if info:
            click.echo(f"Format: {info.format.value}")
            click.echo(f"Pages: {info.page_count}")
            click.echo(f"Images: {info.image_count}")
            click.echo(f"Size: {info.file_size_bytes:,} bytes")
