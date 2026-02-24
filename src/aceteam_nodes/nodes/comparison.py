"""Comparison and logical operator nodes."""

from functools import cached_property
from typing import Literal

from overrides import override
from pydantic import Field
from workflow_engine import (
    BooleanValue,
    Context,
    Data,
    Empty,
    FloatValue,
    Node,
    NodeTypeInfo,
    Params,
)


class ComparisonParams(Params):
    pass


class ComparisonInput(Data):
    a: FloatValue = Field(
        title="A",
        description="The left value in the comparison.",
    )
    b: FloatValue = Field(
        title="B",
        description="The right value in the comparison.",
    )


class ComparisonOutput(Data):
    result: BooleanValue = Field(
        title="Result",
        description="The result of the comparison.",
    )


class LogicalInput(Data):
    a: BooleanValue
    b: BooleanValue


class NotInput(Data):
    a: BooleanValue


class LogicalOutput(Data):
    result: BooleanValue


# --- Comparison Nodes ---


class EqualNode(Node[ComparisonInput, ComparisonOutput, ComparisonParams]):
    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="Equal",
        display_name="Equal",
        description="Outputs true if the two input values are equal.",
        version="1.0.1",
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
    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="NotEqual",
        display_name="Not Equal",
        description="Outputs true if the two input values are not equal.",
        version="1.0.1",
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
    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="GreaterThan",
        display_name="Greater Than",
        description="Outputs true if the first value is greater than the second.",
        version="1.0.1",
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
    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="GreaterThanEqual",
        display_name="Greater Than or Equal",
        description="Outputs true if the first value is greater than or equal to the second.",
        version="1.0.1",
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
    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="LessThan",
        display_name="Less Than",
        description="Outputs true if the first value is less than the second.",
        version="1.0.1",
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
    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="LessThanEqual",
        display_name="Less Than or Equal",
        description="Outputs true if the first value is less than or equal to the second.",
        version="1.0.1",
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


class AndNode(Node[LogicalInput, LogicalOutput, Empty]):
    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="And",
        display_name="Logical AND",
        description="Outputs true only when all inputs are true.",
        version="1.0.1",
        parameter_type=Empty,
    )
    type: Literal["And"] = "And"

    @cached_property
    def input_type(self):
        return LogicalInput

    @cached_property
    def output_type(self):
        return LogicalOutput

    @override
    async def run(
        self,
        context: Context,
        input: LogicalInput,
    ) -> LogicalOutput:
        return LogicalOutput(result=BooleanValue(input.a.root and input.b.root))


class OrNode(Node[LogicalInput, LogicalOutput, Empty]):
    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="Or",
        display_name="Logical OR",
        description="Outputs true when at least one input is true.",
        version="1.0.1",
        parameter_type=Empty,
    )
    type: Literal["Or"] = "Or"

    @cached_property
    def input_fields_info(self):
        return LogicalInput

    @property
    def output_type(self):
        return LogicalOutput

    @override
    async def run(
        self,
        context: Context,
        input: LogicalInput,
    ) -> LogicalOutput:
        return LogicalOutput(result=BooleanValue(input.a.root or input.b.root))


class NotNode(Node[NotInput, LogicalOutput, Empty]):
    TYPE_INFO = NodeTypeInfo.from_parameter_type(
        name="Not",
        display_name="Logical NOT",
        description="Returns the opposite of the input value.",
        version="1.0.1",
        parameter_type=Empty,
    )
    type: Literal["Not"] = "Not"

    @cached_property
    def input_type(self):
        return NotInput

    @cached_property
    def output_type(self):
        return LogicalOutput

    @override
    async def run(
        self,
        context: Context,
        input: NotInput,
    ) -> LogicalOutput:
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
