"""CLI execution context extending workflow-engine's LocalContext."""

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from overrides import override
from workflow_engine import (
    Data,
    DataMapping,
    Node,
    WorkflowErrors,
    WorkflowExecutionResult,
)
from workflow_engine.contexts import LocalContext
from workflow_engine.core import ValidatedWorkflow


class CLIContext(LocalContext):
    """
    Extends LocalContext with LLM support via aceteam-aep and console output hooks.

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

    def _resolve_api_key(self, model: str) -> str:
        """Resolve API key from config or environment based on model name."""
        import os

        if key := self.config.get("api_key"):
            return key
        m = model.lower()
        if m.startswith("claude") or "anthropic" in m:
            return os.environ.get("ANTHROPIC_API_KEY", "")
        if m.startswith("gemini") or "google" in m:
            return os.environ.get("GOOGLE_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        if m.startswith("ollama"):
            return ""
        # Default: OpenAI
        return os.environ.get("OPENAI_API_KEY", "")

    async def call_llm(self, model: str, system_prompt: str, prompt: str) -> str:
        """LLM call via aceteam-aep (supports OpenAI, Anthropic, Google, and more)."""
        from aceteam_aep import ChatMessage, create_client

        # Apply model override from config if set
        model = self.config.get("default_model", model)
        api_key = self._resolve_api_key(model)

        client = create_client(model, api_key=api_key)
        messages: list[ChatMessage] = []
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        messages.append(ChatMessage(role="user", content=prompt))

        response = await client.chat(messages)
        return response.message.text

    @override
    async def on_node_start(
        self,
        *,
        node: Node,
        input_type: type[Data],
        output_type: type[Data],
        input: DataMapping,
    ) -> DataMapping | None:
        result = await super().on_node_start(
            node=node,
            input_type=input_type,
            output_type=output_type,
            input=input,
        )
        if self.verbose:
            print(f"  [{node.type}] running...", file=sys.stderr)
        return result

    @override
    async def on_node_finish(
        self,
        *,
        node: Node,
        input_type: type[Data],
        output_type: type[Data],
        input: DataMapping,
        output: DataMapping,
    ) -> DataMapping:
        result = await super().on_node_finish(
            node=node,
            input_type=input_type,
            output_type=output_type,
            input=input,
            output=output,
        )
        if self.verbose:
            print(f"  [{node.type}] done", file=sys.stderr)
        return result

    @override
    async def on_node_error(
        self,
        *,
        node: Node,
        input_type: type[Data],
        output_type: type[Data],
        input: DataMapping,
        exception: Exception,
    ) -> Exception | DataMapping:
        result = await super().on_node_error(
            node=node,
            input_type=input_type,
            output_type=output_type,
            input=input,
            exception=exception,
        )
        if self.verbose:
            print(f"  [{node.type}] error: {exception}", file=sys.stderr)
        return result

    @override
    async def on_workflow_start(
        self,
        *,
        workflow: ValidatedWorkflow,
        input: DataMapping,
    ) -> WorkflowExecutionResult | None:
        result = await super().on_workflow_start(
            workflow=workflow,
            input=input,
        )
        if self.verbose:
            print(f"Workflow started ({len(workflow.nodes)} nodes)", file=sys.stderr)
        return result

    @override
    async def on_workflow_finish(
        self,
        *,
        workflow: ValidatedWorkflow,
        input: DataMapping,
        output: DataMapping,
    ) -> WorkflowExecutionResult:
        result = await super().on_workflow_finish(
            workflow=workflow,
            input=input,
            output=output,
        )
        if self.verbose:
            print("Workflow completed successfully", file=sys.stderr)
        return result

    @override
    async def on_workflow_error(
        self,
        *,
        workflow: ValidatedWorkflow,
        input: DataMapping,
        errors: WorkflowErrors,
        partial_output: DataMapping,
        node_yields: Mapping[str, str],
    ) -> WorkflowExecutionResult:
        result = await super().on_workflow_error(
            workflow=workflow,
            input=input,
            errors=errors,
            partial_output=partial_output,
            node_yields=node_yields,
        )
        if self.verbose:
            print(f"Workflow completed with errors: {errors}", file=sys.stderr)
        return result


__all__ = [
    "CLIContext",
]
