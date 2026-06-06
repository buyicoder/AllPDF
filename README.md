# AllPDF

Local PDF conversion toolkit — Office ↔ PDF with CLI and MCP Server.

## Quick Start

```bash
# Install
pip install -e ".[all]"

# Convert Office to PDF
allpdf convert report.docx
allpdf convert sheet.xlsx
allpdf convert slides.pptx

# Convert PDF to Office
allpdf convert document.pdf --to docx
allpdf convert table.pdf --to xlsx
allpdf convert deck.pdf --to pptx

# With quality checks
allpdf convert document.pdf --to docx --quality-check

# Batch convert
allpdf batch "*.docx" --to pdf --output-dir ./pdfs

# Check quality of existing conversion
allpdf check source.pdf result.docx

# Show file info
allpdf info document.pdf

# List supported formats
allpdf formats
```

## Requirements

- Python 3.11+
- LibreOffice 7.4+ (for Office → PDF conversion)
- Optional: Java (for tabula-py PDF table extraction)

## Architecture

```
Interface Layer:   CLI (click)  |  MCP Server (mcp/python-sdk)
Orchestration:     Engine routing, quality checks, retry logic
Engine Layer:      LibreOffice, pdf2docx, tabula+camelot, PyMuPDF
Foundation:        Models, utilities, file management
```

## Supported Conversions

| From | To | Engine |
|------|----|--------|
| DOCX | PDF | LibreOffice |
| XLSX | PDF | LibreOffice |
| PPTX | PDF | LibreOffice |
| PDF | DOCX | pdf2docx + PyMuPDF |
| PDF | XLSX | tabula + camelot + openpyxl |
| PDF | PPTX | PyMuPDF + python-pptx |

## AI Integration

AllPDF exposes an MCP Server for AI agents:

```json
{
  "mcpServers": {
    "allpdf": {
      "command": "python",
      "args": ["-m", "allpdf.mcp.server"]
    }
  }
}
```

Tools: `convert_file`, `analyze_file`, `check_quality`, `list_engines`, `get_supported_formats`

When called via MCP, `convert_file` automatically runs:
1. File analysis (format, pages, images, scanned?)
2. Optimal engine selection
3. Conversion execution
4. Quality checks (5 dimensions)
5. Retry with alternative engine if quality below threshold
