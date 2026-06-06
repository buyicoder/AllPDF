# allpdf/cli/batch.py
import glob as glob_mod
import click
from allpdf.orchestrator import Orchestrator
from allpdf.models import FileFormat
from allpdf.utils import ensure_dir


@click.command()
@click.argument("pattern")
@click.option("--to", "target_format", default="pdf", help="Target format")
@click.option("--output-dir", "-d", default=None, help="Output directory")
def batch(pattern, target_format, output_dir):
    """Convert multiple files at once."""
    files = glob_mod.glob(pattern)
    if not files:
        click.echo(f"No files matching: {pattern}")
        raise SystemExit(1)

    dst_fmt = FileFormat(target_format)
    out_dir = ensure_dir(output_dir) if output_dir else None
    orch = Orchestrator()
    success, failed = 0, 0

    click.echo(f"Batch converting {len(files)} file(s) to {target_format.upper()}")

    for f in files:
        if out_dir:
            from pathlib import Path
            out_path = str(out_dir / (Path(f).stem + "." + target_format))
        else:
            from allpdf.utils import temp_output_path
            out_path = temp_output_path(f, target_format)

        try:
            result = orch.convert_auto(f, out_path, dst_fmt)
            if result.status.value == "success":
                success += 1
                click.echo(f"  OK {f} ({result.duration_seconds:.1f}s)")
            else:
                failed += 1
                click.echo(f"  FAIL {f}: {result.error_message}")
        except Exception as e:
            failed += 1
            click.echo(f"  FAIL {f}: {e}")

    click.echo(f"\nDone: {success} succeeded, {failed} failed")
    if failed > 0:
        raise SystemExit(1)
