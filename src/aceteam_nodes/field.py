"""Field types and field info models for AceTeam nodes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from csv import DictReader, DictWriter
from io import StringIO
from typing import Any, ClassVar, TypeVar

from workflow_engine import Context, Data
from workflow_engine.core.values.value import ValueRegistry
from workflow_engine.files import TextFileValue

# Value subclasses auto-register in workflow_engine's value type registry.
# When used alongside a platform that defines the same types (e.g., aceteam-8),
# we reuse the already-registered class to avoid duplicate registration errors.


def _get_or_define_value_type(name: str, cls_factory):
    """Return existing registered class or define a new one."""
    cls = ValueRegistry.DEFAULT.get_value_class(name)
    if cls is not None:
        return cls
    return cls_factory()


def _make_csv_file_value():
    class CSVFileValue(TextFileValue):
        """A CSV file."""

        mime_type: ClassVar[str] = "text/csv"

        async def read_data(self, context: Context) -> Sequence[Mapping[str, Any]]:
            text = await self.read_text(context)
            text_io = StringIO(text)
            reader = DictReader(text_io)
            return tuple(reader)

        async def write_data(self, context: Context, data: Sequence[Mapping[str, Any]]):
            text_io = StringIO()
            writer = DictWriter(text_io, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            text = text_io.getvalue()
            return await self.write_text(context, text)

    return CSVFileValue


CSVFileValue = _get_or_define_value_type("CSVFileValue", _make_csv_file_value)


D = TypeVar("D", bound=Data)


__all__ = [
    "CSVFileValue",
]
