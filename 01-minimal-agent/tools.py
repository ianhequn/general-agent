import json
import os
import subprocess
from pathlib import Path
from typing import Any

#工具调用层 
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a terminal command in the project workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The terminal command to execute.",
                    }
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish_task",
            "description": "Report that the requested task is complete.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "A short summary of the result.",
                    }
                },
                "required": ["summary"],
                "additionalProperties": False,
            },
        },
    },
]


def run_command(
    command: str,
    workspace: Path,
    timeout: int,
) -> dict[str, Any]:
    """Run one shell command and return its result as structured data."""
    if not command.strip():
        return {
            "ok": False,
            "output": "",
            "returncode": None,
            "timed_out": False,
            "error": "command must not be empty",
        }

    if timeout <= 0:
        return {
            "ok": False,
            "output": "",
            "returncode": None,
            "timed_out": False,
            "error": "timeout must be greater than zero",
        }

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=workspace,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return {
            "ok": result.returncode == 0,
            "output": result.stdout,
            "returncode": result.returncode,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return {
            "ok": False,
            "output": output,
            "returncode": None,
            "timed_out": True,
        }
    except OSError as exc:
        return {
            "ok": False,
            "output": "",
            "returncode": None,
            "timed_out": False,
            "error": str(exc),
        }


def dispatch_tool(
    name: str,
    arguments_json: str,
    workspace: Path,
    timeout: int,
) -> dict[str, Any]:
    """Validate a model tool call and dispatch it to the local implementation."""
    try:
        arguments = json.loads(arguments_json)
    except (json.JSONDecodeError, TypeError) as exc:
        return {"ok": False, "error": f"Invalid tool arguments JSON: {exc}"}

    if not isinstance(arguments, dict):
        return {"ok": False, "error": "Tool arguments must be a JSON object."}

    if name == "run_command":
        if set(arguments) != {"command"}:
            return {
                "ok": False,
                "error": "run_command requires exactly one argument: command",
            }
        command = arguments["command"]
        if not isinstance(command, str) or not command.strip():
            return {"ok": False, "error": "command must be a non-empty string."}
        return run_command(command, workspace, timeout)

    if name == "finish_task":
        if set(arguments) != {"summary"}:
            return {
                "ok": False,
                "error": "finish_task requires exactly one argument: summary",
            }
        summary = arguments["summary"]
        if not isinstance(summary, str) or not summary.strip():
            return {"ok": False, "error": "summary must be a non-empty string."}
        return {"ok": True, "finished": True, "summary": summary.strip()}

    return {"ok": False, "error": f"Unknown tool: {name}"}
