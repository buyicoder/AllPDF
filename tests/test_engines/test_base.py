# tests/test_engines/test_base.py
import pytest
from allpdf.engines.base import ConversionEngine
from allpdf.models import FileFormat


class _FakeEngine(ConversionEngine):
    name = "fake"
    input_format = FileFormat.PDF
    output_format = FileFormat.DOCX

    def convert(self, input_path, output_path, **options):
        from allpdf.models import ConversionResult, ConversionStatus
        from pathlib import Path
        return ConversionResult(
            input_path=Path(input_path),
            output_path=Path(output_path),
            input_format=FileFormat.PDF,
            output_format=FileFormat.DOCX,
            status=ConversionStatus.SUCCESS,
            engine_used="fake",
            duration_seconds=0.1,
        )


class TestConversionEngine:
    def test_subclass_must_define_name(self):
        engine = _FakeEngine()
        assert engine.name == "fake"

    def test_subclass_must_define_formats(self):
        engine = _FakeEngine()
        assert engine.input_format == FileFormat.PDF
        assert engine.output_format == FileFormat.DOCX

    def test_is_available_defaults_true(self):
        engine = _FakeEngine()
        assert engine.is_available() is True

    def test_convert_returns_result(self):
        engine = _FakeEngine()
        result = engine.convert("/tmp/in.pdf", "/tmp/out.docx")
        assert result.status.value == "success"
        assert result.engine_used == "fake"

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            ConversionEngine()
