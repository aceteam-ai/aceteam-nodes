"""Comparison and logical operator nodes."""

from functools import cached_property
from typing import Literal

from overrides import override
from workflow_engine import BooleanValue, Context, Data, FloatValue, Node, NodeTypeInfo, Params


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


class EqualNode(Node[ComparisonInput, ComparisonOutput, ComparisonParams]):
    """Checks if a == b."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="Equal",
        display_name="Equal",
        description="Checks if two numbers are equal (a == b).",
        version="1.0.0",
        parameter_type=ComparisonParams,
    )
    type: Literal["Equal"] = "Equal"

    @cached_property
    def input_type(self):
        return ComparisonInput

    @cached_property
    def output_type(self):
        return ComparisonOutput

    @override
    async def run(self, context: Context, input: ComparisonInput) -> ComparisonOutput:
        return ComparisonOutput(result=BooleanValue(input.a.root == input.b.root))


class NotEqualNode(Node[ComparisonInput, ComparisonOutput, ComparisonParams]):
    """Checks if a != b."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="NotEqual",
        display_name="Not Equal",
        description="Checks if two numbers are not equal (a != b).",
        version="1.0.0",
        parameter_type=ComparisonParams,
    )
    type: Literal["NotEqual"] = "NotEqual"

    @cached_property
    def input_type(self):
        return ComparisonInput

    @cached_property
    def output_type(self):
        return ComparisonOutput

    @override
    async def run(self, context: Context, input: ComparisonInput) -> ComparisonOutput:
        return ComparisonOutput(result=BooleanValue(input.a.root != input.b.root))


class GreaterThanNode(Node[ComparisonInput, ComparisonOutput, ComparisonParams]):
    """Checks if a > b."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="GreaterThan",
        display_name="Greater Than",
        description="Checks if a > b.",
        version="1.0.0",
        parameter_type=ComparisonParams,
    )
    type: Literal["GreaterThan"] = "GreaterThan"

    @cached_property
    def input_type(self):
        return ComparisonInput

    @cached_property
    def output_type(self):
        return ComparisonOutput

    @override
    async def run(self, context: Context, input: ComparisonInput) -> ComparisonOutput:
        return ComparisonOutput(result=BooleanValue(input.a.root > input.b.root))


class GreaterThanEqualNode(Node[ComparisonInput, ComparisonOutput, ComparisonParams]):
    """Checks if a >= b."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="GreaterThanEqual",
        display_name="Greater Than or Equal",
        description="Checks if a >= b.",
        version="1.0.0",
        parameter_type=ComparisonParams,
    )
    type: Literal["GreaterThanEqual"] = "GreaterThanEqual"

    @cached_property
    def input_type(self):
        return ComparisonInput

    @cached_property
    def output_type(self):
        return ComparisonOutput

    @override
    async def run(self, context: Context, input: ComparisonInput) -> ComparisonOutput:
        return ComparisonOutput(result=BooleanValue(input.a.root >= input.b.root))


class LessThanNode(Node[ComparisonInput, ComparisonOutput, ComparisonParams]):
    """Checks if a < b."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="LessThan",
        display_name="Less Than",
        description="Checks if a < b.",
        version="1.0.0",
        parameter_type=ComparisonParams,
    )
    type: Literal["LessThan"] = "LessThan"

    @cached_property
    def input_type(self):
        return ComparisonInput

    @cached_property
    def output_type(self):
        return ComparisonOutput

    @override
    async def run(self, context: Context, input: ComparisonInput) -> ComparisonOutput:
        return ComparisonOutput(result=BooleanValue(input.a.root < input.b.root))


class LessThanEqualNode(Node[ComparisonInput, ComparisonOutput, ComparisonParams]):
    """Checks if a <= b."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="LessThanEqual",
        display_name="Less Than or Equal",
        description="Checks if a <= b.",
        version="1.0.0",
        parameter_type=ComparisonParams,
    )
    type: Literal["LessThanEqual"] = "LessThanEqual"

    @cached_property
    def input_type(self):
        return ComparisonInput

    @cached_property
    def output_type(self):
        return ComparisonOutput

    @override
    async def run(self, context: Context, input: ComparisonInput) -> ComparisonOutput:
        return ComparisonOutput(result=BooleanValue(input.a.root <= input.b.root))


# --- Logical Nodes ---


class AndNode(Node[LogicalInput, LogicalOutput, LogicalParams]):
    """Logical AND (a && b)."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="And",
        display_name="Logical AND",
        description="Logical AND (a && b).",
        version="1.0.0",
        parameter_type=LogicalParams,
    )
    type: Literal["And"] = "And"

    @cached_property
    def input_type(self):
        return LogicalInput

    @cached_property
    def output_type(self):
        return LogicalOutput

    @override
    async def run(self, context: Context, input: LogicalInput) -> LogicalOutput:
        return LogicalOutput(result=BooleanValue(input.a.root and input.b.root))


class OrNode(Node[LogicalInput, LogicalOutput, LogicalParams]):
    """Logical OR (a || b)."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="Or",
        display_name="Logical OR",
        description="Logical OR (a || b).",
        version="1.0.0",
        parameter_type=LogicalParams,
    )
    type: Literal["Or"] = "Or"

    @cached_property
    def input_fields_info(self):
        return LogicalInput

    @property
    def output_type(self):
        return LogicalOutput

    @override
    async def run(self, context: Context, input: LogicalInput) -> LogicalOutput:
        return LogicalOutput(result=BooleanValue(input.a.root or input.b.root))


class NotNode(Node[NotInput, LogicalOutput, LogicalParams]):
    """Logical NOT (!a)."""

    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="Not",
        display_name="Logical NOT",
        description="Logical NOT (!a).",
        version="1.0.0",
        parameter_type=LogicalParams,
    )
    type: Literal["Not"] = "Not"

    @cached_property
    def input_type(self):
        return NotInput

    @cached_property
    def output_type(self):
        return LogicalOutput

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
