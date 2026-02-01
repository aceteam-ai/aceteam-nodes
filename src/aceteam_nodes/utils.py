"""Utility functions for AceTeam nodes."""

import re
from collections.abc import Mapping
from typing import Any

from jinja2 import BaseLoader, Environment, select_autoescape
from workflow_engine import DataMapping


def format_string(
    text: str,
    variables: Mapping[str, str],
    iterations: int = 1,
) -> str:
    """Format a string containing variables in the form {name} with their values."""
    assert iterations > 0

    if len(variables) == 0:
        return text

    for key in variables.keys():
        assert "{" not in key and "}" not in key, (
            f"Variable name must not contain curly braces: {key}"
        )

    pattern = re.compile("|".join(re.escape("{" + key + "}") for key in variables.keys()))

    for _ in range(iterations):
        next_text = pattern.sub(lambda match: variables[match.group(0)[1:-1]], text)
        if next_text == text:
            break
        text = next_text

    return text


def format_jinja(
    template_string: str,
    variables: Mapping[str, Any] | None = None,
    auto_escape: bool = True,
) -> str:
    """Render a Jinja2 template string with the provided variables."""
    if variables is None:
        variables = {}

    env = Environment(
        loader=BaseLoader(),
        autoescape=select_autoescape() if auto_escape else False,
    )

    template = env.from_string(template_string)
    return template.render(**variables)


def dump_data_mapping(mapping: DataMapping) -> Mapping[str, Any]:
    return {name: value.model_dump() for name, value in mapping.items()}


__all__ = [
    "dump_data_mapping",
    "format_jinja",
    "format_string",
]
