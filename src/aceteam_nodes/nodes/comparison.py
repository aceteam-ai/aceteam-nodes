"""Comparison and logical operator nodes."""

from typing import Literal

from overrides import override
from workflow_engine import BooleanValue, Context, Data, FloatValue, Params
from workflow_engine.core import NodeTypeInfo as WENodeTypeInfo

from ..field import FieldInfo, FieldType
from ..node_base import AceTeamNode
from ..node_info import NodeTypeInfo


class ComparisonParams(Params):
    pass


class ComparisonInput(Data):
    a: FloatValue
    b: FloatValue


class ComparisonOutput(Data):
    result: BooleanValue


class LogicalParams(Params):
    pass


class LogicalInput(Data):
    a: BooleanValue
    b: BooleanValue


class NotInput(Data):
    a: BooleanValue


class LogicalOutput(Data):
    result: BooleanValue


# --- Comparison Nodes ---


class EqualNode(AceTeamNode[ComparisonInput, ComparisonOutput, ComparisonParams]):
    """Checks if a == b."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="Equal",
        display_name="Equal",
        description="Checks if two numbers are equal (a == b).",
        version="0.4.0",
        parameter_type=ComparisonParams,
    )
    type: Literal["Equal"] = "Equal"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="Equal",
            display_name="Equal",
            description="Checks if two numbers are equal (a == b).",
            params=(),
        )

    @property
    def input_fields_info(self):
        return (
            FieldInfo(
                name="a",
                display_name="First Number",
                type=FieldType.NUMBER,
                description="First number.",
            ),
            FieldInfo(
                name="b",
                display_name="Second Number",
                type=FieldType.NUMBER,
                description="Second number.",
            ),
        )

    @property
    def output_fields_info(self):
        return (
            FieldInfo(
                name="result",
                display_name="Result",
                type=FieldType.BOOLEAN,
                description="True if a == b.",
            ),
        )

    @override
    async def run(self, context: Context, input: ComparisonInput) -> ComparisonOutput:
        return ComparisonOutput(result=BooleanValue(input.a.root == input.b.root))


class NotEqualNode(AceTeamNode[ComparisonInput, ComparisonOutput, ComparisonParams]):
    """Checks if a != b."""

    type: Literal["NotEqual"] = "NotEqual"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="NotEqual",
            display_name="Not Equal",
            description="Checks if two numbers are not equal (a != b).",
            params=(),
        )

    @property
    def input_fields_info(self):
        return (
            FieldInfo(
                name="a",
                display_name="First Number",
                type=FieldType.NUMBER,
                description="First number.",
            ),
            FieldInfo(
                name="b",
                display_name="Second Number",
                type=FieldType.NUMBER,
                description="Second number.",
            ),
        )

    @property
    def output_fields_info(self):
        return (
            FieldInfo(
                name="result",
                display_name="Result",
                type=FieldType.BOOLEAN,
                description="True if a != b.",
            ),
        )

    @override
    async def run(self, context: Context, input: ComparisonInput) -> ComparisonOutput:
        return ComparisonOutput(result=BooleanValue(input.a.root != input.b.root))


class GreaterThanNode(AceTeamNode[ComparisonInput, ComparisonOutput, ComparisonParams]):
    """Checks if a > b."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="GreaterThan",
        display_name="Greater Than",
        description="Checks if a > b.",
        version="0.4.0",
        parameter_type=ComparisonParams,
    )
    type: Literal["GreaterThan"] = "GreaterThan"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="GreaterThan",
            display_name="Greater Than",
            description="Checks if a > b.",
            params=(),
        )

    @property
    def input_fields_info(self):
        return (
            FieldInfo(
                name="a",
                display_name="First Number",
                type=FieldType.NUMBER,
                description="First number.",
            ),
            FieldInfo(
                name="b",
                display_name="Second Number",
                type=FieldType.NUMBER,
                description="Second number.",
            ),
        )

    @property
    def output_fields_info(self):
        return (
            FieldInfo(
                name="result",
                display_name="Result",
                type=FieldType.BOOLEAN,
                description="True if a > b.",
            ),
        )

    @override
    async def run(self, context: Context, input: ComparisonInput) -> ComparisonOutput:
        return ComparisonOutput(result=BooleanValue(input.a.root > input.b.root))


class GreaterThanEqualNode(AceTeamNode[ComparisonInput, ComparisonOutput, ComparisonParams]):
    """Checks if a >= b."""

    type: Literal["GreaterThanEqual"] = "GreaterThanEqual"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="GreaterThanEqual",
            display_name="Greater Than or Equal",
            description="Checks if a >= b.",
            params=(),
        )

    @property
    def input_fields_info(self):
        return (
            FieldInfo(
                name="a",
                display_name="First Number",
                type=FieldType.NUMBER,
                description="First number.",
            ),
            FieldInfo(
                name="b",
                display_name="Second Number",
                type=FieldType.NUMBER,
                description="Second number.",
            ),
        )

    @property
    def output_fields_info(self):
        return (
            FieldInfo(
                name="result",
                display_name="Result",
                type=FieldType.BOOLEAN,
                description="True if a >= b.",
            ),
        )

    @override
    async def run(self, context: Context, input: ComparisonInput) -> ComparisonOutput:
        return ComparisonOutput(result=BooleanValue(input.a.root >= input.b.root))


class LessThanNode(AceTeamNode[ComparisonInput, ComparisonOutput, ComparisonParams]):
    """Checks if a < b."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="LessThan",
        display_name="Less Than",
        description="Checks if a < b.",
        version="0.4.0",
        parameter_type=ComparisonParams,
    )
    type: Literal["LessThan"] = "LessThan"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="LessThan",
            display_name="Less Than",
            description="Checks if a < b.",
            params=(),
        )

    @property
    def input_fields_info(self):
        return (
            FieldInfo(
                name="a",
                display_name="First Number",
                type=FieldType.NUMBER,
                description="First number.",
            ),
            FieldInfo(
                name="b",
                display_name="Second Number",
                type=FieldType.NUMBER,
                description="Second number.",
            ),
        )

    @property
    def output_fields_info(self):
        return (
            FieldInfo(
                name="result",
                display_name="Result",
                type=FieldType.BOOLEAN,
                description="True if a < b.",
            ),
        )

    @override
    async def run(self, context: Context, input: ComparisonInput) -> ComparisonOutput:
        return ComparisonOutput(result=BooleanValue(input.a.root < input.b.root))


class LessThanEqualNode(AceTeamNode[ComparisonInput, ComparisonOutput, ComparisonParams]):
    """Checks if a <= b."""

    type: Literal["LessThanEqual"] = "LessThanEqual"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="LessThanEqual",
            display_name="Less Than or Equal",
            description="Checks if a <= b.",
            params=(),
        )

    @property
    def input_fields_info(self):
        return (
            FieldInfo(
                name="a",
                display_name="First Number",
                type=FieldType.NUMBER,
                description="First number.",
            ),
            FieldInfo(
                name="b",
                display_name="Second Number",
                type=FieldType.NUMBER,
                description="Second number.",
            ),
        )

    @property
    def output_fields_info(self):
        return (
            FieldInfo(
                name="result",
                display_name="Result",
                type=FieldType.BOOLEAN,
                description="True if a <= b.",
            ),
        )

    @override
    async def run(self, context: Context, input: ComparisonInput) -> ComparisonOutput:
        return ComparisonOutput(result=BooleanValue(input.a.root <= input.b.root))


# --- Logical Nodes ---


class AndNode(AceTeamNode[LogicalInput, LogicalOutput, LogicalParams]):
    """Logical AND (a && b)."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="And",
        display_name="Logical AND",
        description="Logical AND (a && b).",
        version="0.4.0",
        parameter_type=LogicalParams,
    )
    type: Literal["And"] = "And"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="And",
            display_name="Logical AND",
            description="Logical AND (a && b).",
            params=(),
        )

    @property
    def input_fields_info(self):
        return (
            FieldInfo(
                name="a",
                display_name="First Boolean",
                type=FieldType.BOOLEAN,
                description="First boolean.",
            ),
            FieldInfo(
                name="b",
                display_name="Second Boolean",
                type=FieldType.BOOLEAN,
                description="Second boolean.",
            ),
        )

    @property
    def output_fields_info(self):
        return (
            FieldInfo(
                name="result", display_name="Result", type=FieldType.BOOLEAN, description="a AND b."
            ),
        )

    @override
    async def run(self, context: Context, input: LogicalInput) -> LogicalOutput:
        return LogicalOutput(result=BooleanValue(input.a.root and input.b.root))


class OrNode(AceTeamNode[LogicalInput, LogicalOutput, LogicalParams]):
    """Logical OR (a || b)."""

    type: Literal["Or"] = "Or"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="Or",
            display_name="Logical OR",
            description="Logical OR (a || b).",
            params=(),
        )

    @property
    def input_fields_info(self):
        return (
            FieldInfo(
                name="a",
                display_name="First Boolean",
                type=FieldType.BOOLEAN,
                description="First boolean.",
            ),
            FieldInfo(
                name="b",
                display_name="Second Boolean",
                type=FieldType.BOOLEAN,
                description="Second boolean.",
            ),
        )

    @property
    def output_fields_info(self):
        return (
            FieldInfo(
                name="result", display_name="Result", type=FieldType.BOOLEAN, description="a OR b."
            ),
        )

    @override
    async def run(self, context: Context, input: LogicalInput) -> LogicalOutput:
        return LogicalOutput(result=BooleanValue(input.a.root or input.b.root))


class NotNode(AceTeamNode[NotInput, LogicalOutput, LogicalParams]):
    """Logical NOT (!a)."""

    type: Literal["Not"] = "Not"

    @classmethod
    @override
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="Not",
            display_name="Logical NOT",
            description="Logical NOT (!a).",
            params=(),
        )

    @property
    def input_fields_info(self):
        return (
            FieldInfo(
                name="a",
                display_name="Boolean Value",
                type=FieldType.BOOLEAN,
                description="Value to negate.",
            ),
        )

    @property
    def output_fields_info(self):
        return (
            FieldInfo(
                name="result", display_name="Result", type=FieldType.BOOLEAN, description="NOT a."
            ),
        )

    @override
    async def run(self, context: Context, input: NotInput) -> LogicalOutput:
        return LogicalOutput(result=BooleanValue(not input.a.root))


__all__ = [
    "AndNode",
    "EqualNode",
    "GreaterThanEqualNode",
    "GreaterThanNode",
    "LessThanEqualNode",
    "LessThanNode",
    "NotEqualNode",
    "NotNode",
    "OrNode",
]
