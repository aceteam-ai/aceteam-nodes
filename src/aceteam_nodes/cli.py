"""CLI entry point for aceteam-nodes.

Usage:
    python -m aceteam_nodes.cli run workflow.json --input '{"prompt":"Hello"}'
    python -m aceteam_nodes.cli list-nodes
    python -m aceteam_nodes.cli validate workflow.json
"""

import argparse
import asyncio
import json
import sys
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="aceteam-nodes",
        description="AceTeam workflow nodes CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run command
    run_parser = subparsers.add_parser("run", help="Run a workflow from a JSON file")
    run_parser.add_argument("file", help="Path to the workflow JSON file")
    run_parser.add_argument(
        "--input",
        type=str,
        default="{}",
        help="JSON string of input values",
    )
    run_parser.add_argument(
        "--config",
        type=str,
        default="~/.ace/config.yaml",
        help="Path to config file",
    )
    run_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show progress messages",
    )

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a workflow JSON file")
    validate_parser.add_argument("file", help="Path to the workflow JSON file")

    # list-nodes command
    subparsers.add_parser("list-nodes", help="List available node types")

    return parser.parse_args()


async def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    from .execution import run_workflow_from_file

    input_data = json.loads(args.input)
    result = await run_workflow_from_file(
        file_path=args.file,
        input=input_data,
        config_path=args.config,
        verbose=args.verbose,
    )
    return result


def cmd_validate(args: argparse.Namespace) -> dict[str, Any]:
    from .execution import (
        WorkflowDeserializationError,
        WorkflowFileNotFoundError,
        load_workflow_from_file,
    )

    try:
        workflow = load_workflow_from_file(args.file)
        return {
            "valid": True,
            "nodes": len(workflow.nodes),
            "inputs": [f.name for f in workflow.inputs],
            "outputs": [f.name for f in workflow.outputs],
        }
    except WorkflowFileNotFoundError as e:
        return {"valid": False, "error": str(e)}
    except WorkflowDeserializationError as e:
        return {"valid": False, "error": str(e)}


def cmd_list_nodes() -> dict[str, Any]:
    # Import nodes to trigger registration
    from aceteam_nodes.nodes import register_all_nodes; register_all_nodes()  # noqa: E702

    from .node_base import aceteam_nodes as registry

    nodes = []
    for node_cls in registry:
        try:
            info = node_cls.type_info()
            nodes.append({
                "type": info.type,
                "display_name": info.display_name,
                "description": info.description,
            })
        except NotImplementedError:
            pass
    return {"nodes": nodes}


def main():
    args = parse_args()

    try:
        if args.command == "run":
            result = asyncio.run(cmd_run(args))
        elif args.command == "validate":
            result = cmd_validate(args)
        elif args.command == "list-nodes":
            result = cmd_list_nodes()
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            sys.exit(1)

        print(json.dumps(result, indent=2, default=str))

        if args.command == "run" and not result.get("success", True):
            sys.exit(1)

    except Exception as e:
        error_result = {"success": False, "error": str(e)}
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
