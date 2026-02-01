"""Conditional nodes - If and IfElse branching."""

import logging
from collections.abc import Sequence
from functools import cached_property
from typing import Literal

from overrides import override
from pydantic import ConfigDict, Field
from workflow_engine import (
    BooleanValue,
    Context,
    Data,
    Empty,
    JSONValue,
    Params,
)
from workflow_engine.core import NodeTypeInfo as WENodeTypeInfo

from ..field import FieldInfo, FieldType
from ..node_base import AceTeamNode
from ..node_info import NodeTypeInfo
from ..workflow import AceTeamWorkflow

logger = logging.getLogger(__name__)


WORKFLOW_IF_TRUE_FIELD_INFO = FieldInfo(
    name="if_true",
    display_name="Workflow If True",
    type=FieldType.WORKFLOW,
    description="The workflow to run if the condition is true.",
)

WORKFLOW_IF_FALSE_FIELD_INFO = FieldInfo(
    name="if_false",
    display_name="Workflow If False",
    type=FieldType.WORKFLOW,
    description="The workflow to run if the condition is false.",
)

CONDITION_FIELD_INFO = FieldInfo(
    name="condition",
    display_name="Condition",
    type=FieldType.BOOLEAN,
    description="The condition to check.",
)


class IfParams(Params):
    if_true: JSONValue = Field(default_factory=lambda: JSONValue(None))

    @cached_property
    def workflow_if_true(self) -> AceTeamWorkflow:
        return AceTeamWorkflow.model_validate(self.if_true.root)


class IfElseParams(Params):
    if_true: JSONValue = Field(default_factory=lambda: JSONValue(None))
    if_false: JSONValue = Field(default_factory=lambda: JSONValue(None))

    @cached_property
    def workflow_if_true(self) -> AceTeamWorkflow:
        return AceTeamWorkflow.model_validate(self.if_true.root)

    @cached_property
    def workflow_if_false(self) -> AceTeamWorkflow:
        return AceTeamWorkflow.model_validate(self.if_false.root)


class ConditionalInput(Data):
    model_config = ConfigDict(extra="allow")
    condition: BooleanValue


class IfNode(
    AceTeamNode[Data, Empty, IfParams]
):
    """Runs a workflow only if a boolean condition is true."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="If",
        display_name="If",
        description="Runs a workflow only if a boolean condition is true.",
        version="0.4.0",
        parameter_type=IfParams,
    )

    type: Literal["If"] = "If"  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="If",
            display_name="If",
            description="Runs a workflow only if a boolean condition is true.",
            params=(WORKFLOW_IF_TRUE_FIELD_INFO,),
        )

    @cached_property
    def input_fields_info(self) -> Sequence[FieldInfo]:
        true_input_types_by_name = {
            input.name: input.type for input in self.params.workflow_if_true.inputs
        }
        assert "condition" not in true_input_types_by_name, (
            f"{self.type}: condition is a reserved keyword"
        )
        return (CONDITION_FIELD_INFO, *self.params.workflow_if_true.inputs)

    @cached_property
    def output_fields_info(self) -> Sequence[FieldInfo]:
        return self.params.workflow_if_true.outputs

    @override
    async def run(self, context: Context, input: ConditionalInput) -> AceTeamWorkflow | None:
        if input.condition:
            return self.params.workflow_if_true
        else:
            return None


class IfElseNode(
    AceTeamNode[Data, Empty, IfElseParams]
):
    """Runs one of two workflows based on a boolean condition."""

    TYPE_INFO = WENodeTypeInfo.from_parameter_type(
        name="IfElse",
        display_name="If Else",
        description="Runs one of two workflows based on a boolean condition.",
        version="0.4.0",
        parameter_type=IfElseParams,
    )

    type: Literal["IfElse"] = "IfElse"  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    def type_info(cls) -> NodeTypeInfo:
        return NodeTypeInfo(
            type="IfElse",
            display_name="If Else",
            description="Runs one of two workflows based on a boolean condition.",
            params=(WORKFLOW_IF_TRUE_FIELD_INFO, WORKFLOW_IF_FALSE_FIELD_INFO),
        )

    @cached_property
    def input_fields_info(self) -> Sequence[FieldInfo]:
        true_input_types_by_name = {
            input.name: input.type for input in self.params.workflow_if_true.inputs
        }
        false_input_types_by_name = {
            input.name: input.type for input in self.params.workflow_if_false.inputs
        }
        assert true_input_types_by_name == false_input_types_by_name, (
            f"{self.type}: true and false inputs must match"
        )
        assert "condition" not in true_input_types_by_name, (
            f"{self.type}: condition is a reserved keyword"
        )
        return (CONDITION_FIELD_INFO, *self.params.workflow_if_true.inputs)

    @cached_property
    def output_fields_info(self) -> Sequence[FieldInfo]:
        true_output_types_by_name = {
            output.name: output.type for output in self.params.workflow_if_true.outputs
        }
        false_output_types_by_name = {
            output.name: output.type for output in self.params.workflow_if_false.outputs
        }
        assert true_output_types_by_name == false_output_types_by_name, (
            f"{self.type}: true and false outputs must match"
        )
        return self.params.workflow_if_true.outputs

    @override
    async def run(self, context: Context, input: ConditionalInput) -> AceTeamWorkflow:
        if input.condition:
            return self.params.workflow_if_true
        else:
            return self.params.workflow_if_false


__all__ = [
    "IfElseNode",
    "IfElseParams",
    "IfNode",
    "IfParams",
]
