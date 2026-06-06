# allpdf/cli/main.py
import click
from allpdf.cli.convert import convert
from allpdf.cli.batch import batch
from allpdf.cli.check import check
from allpdf.models import FileFormat


@click.group()
@click.version_option(version="0.1.0", prog_name="allpdf")
def cli():
    """AllPDF — Local PDF conversion toolkit.

    Convert between PDF and Office formats with quality checks.
    """


cli.add_command(convert)
cli.add_command(batch)
cli.add_command(check)


@cli.command()
def formats():
    """List all supported conversion directions."""
    from allpdf.orchestrator import Orchestrator
    orch = Orchestrator()
    conversions = orch.get_supported_conversions()
    click.echo("Supported conversions:")
    for c in conversions:
        status = "✓" if c["available"] else "✗"
        click.echo(f"  {status} {c['from']:6s} -> {c['to']:6s}  ({c['engine']})")


@cli.command()
@click.argument("filepath")
def info(filepath: str):
    """Show file information."""
    import os
    from pathlib import Path
    from allpdf.engines.pymupdf_ops import PyMuPDFOps
    from allpdf.utils import detect_format

    if not os.path.exists(filepath):
        click.echo(f"Error: File not found: {filepath}", err=True)
        raise SystemExit(1)

    fmt = detect_format(Path(filepath))
    click.echo(f"File: {filepath}")
    click.echo(f"Format: {fmt.value}")
    click.echo(f"Size: {os.path.getsize(filepath):,} bytes")

    if fmt == FileFormat.PDF:
        ops = PyMuPDFOps()
        info = ops.analyze(filepath)
        if info:
            click.echo(f"Pages: {info.page_count}")
            click.echo(f"Images: {info.image_count}")
            click.echo(f"Scanned: {'Yes' if info.is_scanned else 'No'}")
