"""CLI execution context extending workflow-engine's LocalContext."""

import sys
from pathlib import Path
from typing import Any

import yaml
from overrides import override
from workflow_engine import Node, Workflow, WorkflowErrors
from workflow_engine.contexts.local import LocalContext
from workflow_engine.core import DataMapping


class CLIContext(LocalContext):
    """
    Extends LocalContext with LLM support via litellm and console output hooks.

    Configuration is loaded from ~/.ace/config.yaml which stores API keys
    and model preferences.
    """

    def __init__(
        self,
        config_path: str = "~/.ace/config.yaml",
        base_dir: str = ".ace/runs",
        verbose: bool = False,
    ):
        super().__init__(base_dir=base_dir)
        self.config = self._load_config(config_path)
        self.verbose = verbose

    @staticmethod
    def _load_config(config_path: str) -> dict[str, Any]:
        path = Path(config_path).expanduser()
        if not path.exists():
            return {}
        with open(path) as f:
            return yaml.safe_load(f) or {}

    async def call_llm(self, model: str, system_prompt: str, prompt: str) -> str:
        """LLM call via litellm (supports OpenAI, Anthropic, 100+ providers)."""
        from litellm import acompletion

        # Apply model override from config if set
        model = self.config.get("default_model", model)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await acompletion(model=model, messages=messages)
        return response.choices[0].message.content

    @override
    async def on_node_start(
        self,
        *,
        node: Node,
        input: DataMapping,
    ) -> DataMapping | None:
        result = await super().on_node_start(node=node, input=input)
        if self.verbose:
            print(f"  [{node.type}] running...", file=sys.stderr)
        return result

    @override
    async def on_node_finish(
        self,
        *,
        node: Node,
        input: DataMapping,
        output: DataMapping,
    ) -> DataMapping:
        result = await super().on_node_finish(node=node, input=input, output=output)
        if self.verbose:
            print(f"  [{node.type}] done", file=sys.stderr)
        return result

    @override
    async def on_node_error(
        self,
        *,
        node: Node,
        input: DataMapping,
        exception: Exception,
    ) -> Exception | DataMapping:
        result = await super().on_node_error(node=node, input=input, exception=exception)
        if self.verbose:
            print(f"  [{node.type}] error: {exception}", file=sys.stderr)
        return result

    @override
    async def on_workflow_start(
        self,
        *,
        workflow: Workflow,
        input: DataMapping,
    ) -> tuple[WorkflowErrors, DataMapping] | None:
        result = await super().on_workflow_start(workflow=workflow, input=input)
        if self.verbose:
            print(f"Workflow started ({len(workflow.nodes)} nodes)", file=sys.stderr)
        return result

    @override
    async def on_workflow_finish(
        self,
        *,
        workflow: Workflow,
        input: DataMapping,
        output: DataMapping,
    ) -> DataMapping:
        result = await super().on_workflow_finish(workflow=workflow, input=input, output=output)
        if self.verbose:
            print("Workflow completed successfully", file=sys.stderr)
        return result

    @override
    async def on_workflow_error(
        self,
        *,
        workflow: Workflow,
        input: DataMapping,
        errors: WorkflowErrors,
        partial_output: DataMapping,
    ) -> tuple[WorkflowErrors, DataMapping]:
        result = await super().on_workflow_error(
            workflow=workflow, input=input, errors=errors, partial_output=partial_output
        )
        if self.verbose:
            print(f"Workflow completed with errors: {errors}", file=sys.stderr)
        return result


__all__ = [
    "CLIContext",
]
