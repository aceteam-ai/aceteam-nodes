"""AceTeam workflow model."""

from collections.abc import Mapping, Sequence
from functools import cached_property
from typing import Any

from pydantic import model_validator
from workflow_engine import DataMapping, Workflow

from .field import FieldInfo
from .node_base import AceTeamNode


class AceTeamWorkflow(Workflow):
    nodes: Sequence[AceTeamNode]
    inputs: Sequence[FieldInfo]
    outputs: Sequence[FieldInfo]

    @cached_property
    def inputs_by_key(self) -> Mapping[str, FieldInfo]:
        inputs_by_key: dict[str, FieldInfo] = {}
        for field in self.inputs:
            name = field.name
            assert name not in inputs_by_key, f"Duplicate input field: {name}"
            inputs_by_key[name] = field
        return inputs_by_key

    @cached_property
    def outputs_by_key(self) -> Mapping[str, FieldInfo]:
        outputs_by_key: dict[str, FieldInfo] = {}
        for field in self.outputs:
            name = field.name
            assert name not in outputs_by_key, f"Duplicate output field: {name}"
            outputs_by_key[name] = field
        return outputs_by_key

    @model_validator(mode="after")
    def _validate_input_fields(self):
        for input_edge in self.input_edges:
            input_field = self.inputs_by_key[input_edge.input_key]
            input_type = input_field.python_type
            target = self.nodes_by_id[input_edge.target_id]
            input_edge.validate_types(input_type=input_type, target=target)
        return self

    @model_validator(mode="after")
    def _validate_output_fields(self):
        for output_edge in self.output_edges:
            output_field = self.outputs_by_key[output_edge.output_key]
            output_type = output_field.python_type
            source = self.nodes_by_id[output_edge.source_id]
            output_edge.validate_types(source=source, output_type=output_type)
        return self

    def parse_input(self, input: Mapping[str, Any]) -> DataMapping:
        return {
            field.name: field.python_type.model_validate(input[field.name])
            for field in self.inputs
            if field.name in input
        }

    def parse_output(self, output: Mapping[str, Any]) -> DataMapping:
        return {
            field.name: field.python_type.model_validate(output[field.name])
            for field in self.outputs
            if field.name in output
        }


__all__ = [
    "AceTeamWorkflow",
]
