# allpdf/engines/base.py
from abc import ABC, abstractmethod
from typing import Optional

from allpdf.models import ConversionResult, FileFormat, ConversionStatus


class ConversionEngine(ABC):
    """Abstract base class for all conversion engines.

    Each engine handles one specific conversion direction (e.g., PDF -> DOCX).
    Subclasses must define ``name``, ``input_format``, ``output_format``, and
    ``convert()``.
    """

    name: str = ""
    input_format: FileFormat
    output_format: FileFormat

    @abstractmethod
    def convert(self, input_path: str, output_path: str, **options) -> ConversionResult:
        """Execute the conversion.

        Args:
            input_path: Path to the input file.
            output_path: Desired path for the output file.
            **options: Engine-specific options (pages, dpi, etc.).

        Returns:
            ConversionResult with status, timing, and any error info.
        """
        ...

    def is_available(self) -> bool:
        """Check if this engine's external dependencies are installed.

        Override in subclasses that require system-level dependencies.
        Returns True by default (pure-Python engines).
        """
        return True

    def __repr__(self) -> str:
        return f"<{self.name}: {self.input_format.value} -> {self.output_format.value}>"
