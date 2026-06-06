# allpdf/quality/report.py
"""Quality report formatting utilities."""


def format_report(report: "QualityReport", verbose: bool = False) -> str:
    """Format a QualityReport for terminal display."""
    grade_emoji = {"green": "✓", "yellow": "⚠", "red": "✗"}
    em = grade_emoji.get(report.overall_grade.value, "?")

    lines = [f"  Overall: {em} {report.overall_grade.value.upper()}"]
    for check in report.checks:
        c_em = grade_emoji.get(check.grade.value, "?")
        lines.append(f"    {c_em} {check.name}: {check.detail}")

    return "\n".join(lines)
