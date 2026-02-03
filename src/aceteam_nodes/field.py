"""Field types and field info models for AceTeam nodes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from csv import DictReader, DictWriter
from enum import StrEnum
from functools import cached_property
from io import StringIO
from typing import Any, ClassVar, Literal, Type, TypeVar

from pydantic import BaseModel, create_model, model_validator
from workflow_engine import (
    BooleanValue,
    Context,
    Data,
    FileValue,
    FloatValue,
    JSONValue,
    SequenceValue,
    StringValue,
    Value,
    ValueType,
)
from workflow_engine.core.values.value import value_type_registry
from workflow_engine.files import (
    JSONFileValue,
    JSONLinesFileValue,
    PDFFileValue,
    TextFileValue,
)

# Value subclasses auto-register in workflow_engine's value type registry.
# When used alongside a platform that defines the same types (e.g., aceteam-8),
# we reuse the already-registered class to avoid duplicate registration errors.


def _get_or_define_value_type(name: str, cls_factory):
    """Return existing registered class or define a new one."""
    if name in value_type_registry.types:
        return value_type_registry.types[name]
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


class FieldType(StrEnum):
    """The set of field types supported by AceTeam nodes."""

    BOOLEAN = "boolean"
    FIELD_LIST = "field_list"
    ITERATION_INDEXED_FIELD_LIST = "iteration_indexed_field_list"
    FILE = "file"
    FILE_AUDIO = "file:audio"
    FILE_CSV = "file:csv"
    FILE_JSON = "file:json"
    FILE_JSONLINES = "file:jsonlines"
    FILE_MP3 = "file:mp3"
    FILE_PDF = "file:pdf"
    FILE_TEXT = "file:text"
    FILE_VIDEO = "file:video"
    GANTT_CHART = "gantt_chart"
    GRAPH = "graph"
    JSON = "json"
    LONG_TEXT = "long_text"
    MODEL = "model"
    MODEL_LIST = "model_list"
    NUMBER = "number"
    SEQUENCE = "sequence"
    SHORT_TEXT = "short_text"
    SQL = "sql"
    WORKFLOW = "workflow"


class FieldInfo(BaseModel):
    """Represents metadata for a node field."""

    name: str
    type: FieldType
    display_name: str | None = None
    description: str | None = None
    default: Any | None = None
    type_parameters: Sequence[FieldInfo] = ()

    # specific to number fields
    min: float | None = None
    max: float | None = None
    step: float | None = None

    # specific to SQL fields
    database_connection: str | None = None

    # specific to template fields
    template_parameters: str | None = None

    # specific to text fields - list of options for dropdown/select
    options: Sequence[str] | None = None

    @model_validator(mode="after")
    def _validate_number_fields(self):
        if self.type is not FieldType.NUMBER:
            assert self.min is None
            assert self.max is None
            assert self.step is None

        if self.type is not FieldType.SQL:
            assert self.database_connection is None

        if self.type not in (FieldType.LONG_TEXT, FieldType.SHORT_TEXT):
            assert self.template_parameters is None

        if self.type != FieldType.SHORT_TEXT:
            assert self.options is None

        if self.min is not None and self.max is not None:
            assert self.min <= self.max
        if self.min is not None and self.default is not None:
            assert self.min <= self.default
        if self.max is not None and self.default is not None:
            assert self.default <= self.max

        return self

    @model_validator(mode="after")
    def _validate_sequence_fields(self):
        if self.type is FieldType.SEQUENCE:
            assert len(self.type_parameters) <= 1
        else:
            assert len(self.type_parameters) == 0
        return self

    @property
    def python_type(self) -> ValueType:
        if self.type is FieldType.SEQUENCE:
            if self.type_parameters:
                (element_type,) = self.type_parameters
                return SequenceValue[element_type.python_type]
            return SequenceValue[JSONValue]

        return _non_parametric_field_type_to_type[self.type]


def _make_field_info_value():
    class FieldInfoValue(Value[FieldInfo]):
        @property
        def name(self) -> str:
            return self.root.name

        @property
        def type(self) -> FieldType:
            return self.root.type

        @property
        def display_name(self) -> str | None:
            return self.root.display_name

        @property
        def description(self) -> str | None:
            return self.root.description

        @cached_property
        def default(self) -> Value | None:
            if self.root.default is None:
                return None
            if isinstance(self.root.default, self.python_type):
                return self.root.default
            return self.python_type.model_validate(self.root.default)

        @property
        def min(self) -> float | None:
            return self.root.min

        @property
        def max(self) -> float | None:
            return self.root.max

        @property
        def step(self) -> float | None:
            return self.root.step

        @property
        def database_connection(self) -> str | None:
            return self.root.database_connection

        @property
        def template_parameters(self) -> str | None:
            return self.root.template_parameters

        @property
        def python_type(self) -> ValueType:
            return self.root.python_type

        @property
        def options(self) -> Sequence[str] | None:
            return self.root.options

    return FieldInfoValue


FieldInfoValue = _get_or_define_value_type("FieldInfoValue", _make_field_info_value)


class IterationIndexedFieldInfo(FieldInfo):
    """A field that may be indexed by an iteration index."""

    iteration_index: int | None = None
    expand: Literal[False] = False


def _make_iteration_indexed_field_info_value():
    class IterationIndexedFieldInfoValue(Value[IterationIndexedFieldInfo]):
        @property
        def name(self) -> str:
            return self.root.name

        @property
        def type(self) -> FieldType:
            return self.root.type

        @property
        def display_name(self) -> str | None:
            return self.root.display_name

        @property
        def description(self) -> str | None:
            return self.root.description

        @property
        def default(self) -> Any | None:
            return self.root.default

        @property
        def min(self) -> float | None:
            return self.root.min

        @property
        def max(self) -> float | None:
            return self.root.max

        @property
        def step(self) -> float | None:
            return self.root.step

        @property
        def database_connection(self) -> str | None:
            return self.root.database_connection

        @property
        def template_parameters(self) -> str | None:
            return self.root.template_parameters

        @property
        def python_type(self) -> ValueType:
            return self.root.python_type

        @property
        def options(self) -> Sequence[str] | None:
            return self.root.options

        @property
        def iteration_index(self) -> int | None:
            return self.root.iteration_index

        def to_field_info(self) -> FieldInfo:
            return FieldInfo(
                name=self.name,
                type=self.type,
                display_name=self.display_name,
                description=self.description,
                default=self.default,
                min=self.min,
                max=self.max,
                step=self.step,
                database_connection=self.database_connection,
                template_parameters=self.template_parameters,
                options=self.options,
            )

    return IterationIndexedFieldInfoValue


IterationIndexedFieldInfoValue = _get_or_define_value_type(
    "IterationIndexedFieldInfoValue", _make_iteration_indexed_field_info_value
)


type FieldSequenceValue = SequenceValue[FieldInfoValue]
type IterationIndexedFieldSequenceValue = SequenceValue[IterationIndexedFieldInfoValue]


D = TypeVar("D", bound=Data)


def build_pydantic_model(
    fields_info: Sequence[FieldInfo | FieldInfoValue] | FieldSequenceValue,
    base_cls: Type[D] = Data,
) -> Type[D]:
    if len(fields_info) == 0:
        return base_cls
    if isinstance(fields_info, SequenceValue):
        fields_info = fields_info.root
    return create_model(
        "Input",
        __base__=base_cls,
        **{info.name: info.python_type for info in fields_info},  # type: ignore
    )


_non_parametric_field_type_to_type: Mapping[FieldType, ValueType] = {
    FieldType.BOOLEAN: BooleanValue,
    FieldType.FIELD_LIST: SequenceValue[FieldInfoValue],
    FieldType.ITERATION_INDEXED_FIELD_LIST: SequenceValue[IterationIndexedFieldInfoValue],
    FieldType.FILE: FileValue,
    FieldType.FILE_AUDIO: FileValue,
    FieldType.FILE_CSV: CSVFileValue,
    FieldType.FILE_JSON: JSONFileValue,
    FieldType.FILE_JSONLINES: JSONLinesFileValue,
    FieldType.FILE_MP3: FileValue,
    FieldType.FILE_PDF: PDFFileValue,
    FieldType.FILE_TEXT: TextFileValue,
    FieldType.FILE_VIDEO: FileValue,
    FieldType.GANTT_CHART: JSONValue,
    FieldType.GRAPH: JSONValue,
    FieldType.LONG_TEXT: StringValue,
    FieldType.JSON: JSONValue,
    FieldType.MODEL: StringValue,
    FieldType.MODEL_LIST: SequenceValue[StringValue],
    FieldType.NUMBER: FloatValue,
    FieldType.SHORT_TEXT: StringValue,
    FieldType.SQL: StringValue,
    FieldType.WORKFLOW: JSONValue,
}


__all__ = [
    "CSVFileValue",
    "FieldInfo",
    "FieldInfoValue",
    "FieldSequenceValue",
    "FieldType",
    "IterationIndexedFieldInfo",
    "IterationIndexedFieldInfoValue",
    "IterationIndexedFieldSequenceValue",
    "build_pydantic_model",
]
