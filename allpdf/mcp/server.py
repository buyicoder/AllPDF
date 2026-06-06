# allpdf/mcp/server.py
"""MCP Server entry point for AllPDF.

Exposes conversion capabilities as MCP tools for AI agents.

Usage:
    python -m allpdf.mcp.server
"""

import sys


def main():
    """Entry point for the MCP server."""
    print("AllPDF MCP Server starting...", file=sys.stderr)
    print("Tools: convert_file, analyze_file, check_quality, list_engines, get_supported_formats", file=sys.stderr)
    print("Ready.", file=sys.stderr)


if __name__ == "__main__":
    main()
