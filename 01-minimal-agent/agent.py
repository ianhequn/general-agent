"""Stage 02: a minimal coding agent using native function calling."""

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from tools import TOOL_SCHEMAS, dispatch_tool


SYSTEM_PROMPT = """You are a software engineering agent.
Use tools to inspect, modify, and test the workspace. Call finish_task only after
the requested work has been verified. Do not claim success without evidence."""


class ChatCompletions(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


@dataclass
class AgentResult:
    exit_status: str
    calls: int
    summary: str | None
    messages: list[dict[str, Any]]


def message_to_dict(message: Any) -> dict[str, Any]:
    """Convert an SDK message object to the history shape the API expects."""
    if hasattr(message, "model_dump"):
        # Keep ``content: null`` for a tool-call message: the Chat Completions
        # schema defines content as nullable rather than absent.
        data = message.model_dump()
    elif isinstance(message, dict):
        data = dict(message)
    else:
        data = {"role": message.role, "content": getattr(message, "content", None)}
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            data["tool_calls"] = [
                {"id": call.id, "type": call.type, "function": {
                    "name": call.function.name, "arguments": call.function.arguments,
                }}
                for call in tool_calls
            ]
    return {key: value for key, value in data.items()
            if key in {"role", "content", "tool_calls", "name", "tool_call_id"}}


def run_agent(completions: ChatCompletions, task: str, workspace: Path, *,
              max_calls: int = 10, command_timeout: int = 30) -> AgentResult:
    """Run until finish_task, a call limit, or a model response with no tool call."""
    if max_calls <= 0:
        raise ValueError("max_calls must be greater than zero")

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    for calls in range(1, max_calls + 1):
        response = completions.create(
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"),
            messages=messages, tools=TOOL_SCHEMAS, tool_choice="auto", stream=False,
        )
        message = response.choices[0].message
        messages.append(message_to_dict(message))
        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            return AgentResult("model_stopped", calls, None, messages)

        for tool_call in tool_calls:
            result = dispatch_tool(tool_call.function.name, tool_call.function.arguments,
                                   workspace.resolve(), command_timeout)
            messages.append({
                "role": "tool", "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })
            if result.get("finished"):
                return AgentResult("project_done", calls, result["summary"], messages)
    return AgentResult("call_limit", max_calls, None, messages)


def build_client() -> ChatCompletions:
    """Create the real client only for the CLI; tests inject a fake completion API."""
    from openai import OpenAI

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required for a real model run")
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com").chat.completions


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal native-tool-calling coding agent")
    parser.add_argument("task", help="natural-language task for the agent")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--max-calls", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--trajectory", type=Path, default=Path("trajectory.json"))
    args = parser.parse_args()
    result = run_agent(build_client(), args.task, args.workspace,
                       max_calls=args.max_calls, command_timeout=args.timeout)
    args.trajectory.write_text(json.dumps({
        "messages": result.messages, "exit_status": result.exit_status,
        "now_calls": result.calls, "summary": result.summary,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"exit_status={result.exit_status}; calls={result.calls}")
    if result.summary:
        print(result.summary)


if __name__ == "__main__":
    main()
