import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent import run_agent


def tool_call(call_id, name, arguments):
    return SimpleNamespace(id=call_id, type="function",
        function=SimpleNamespace(name=name, arguments=arguments))


class FakeCompletions:
    def __init__(self, messages):
        self.responses = list(messages)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=self.responses.pop(0))])


class AgentLoopTests(unittest.TestCase):
    def test_executes_tool_and_returns_result_with_matching_id(self):
        fake = FakeCompletions([
            SimpleNamespace(role="assistant", content=None, tool_calls=[
                tool_call("call_1", "run_command", json.dumps({
                    "command": 'python -c "print(42)"',
                }))]),
            SimpleNamespace(role="assistant", content=None, tool_calls=[
                tool_call("call_2", "finish_task", '{"summary": "test passed"}')]),
        ])
        with tempfile.TemporaryDirectory() as directory:
            result = run_agent(fake, "run a test", Path(directory))
        self.assertEqual(result.exit_status, "project_done")
        self.assertEqual(result.summary, "test passed")
        tool_result = result.messages[3]
        self.assertEqual(tool_result["role"], "tool")
        self.assertEqual(tool_result["tool_call_id"], "call_1")
        self.assertIn('"returncode": 0', tool_result["content"])

    def test_returns_call_limit_without_extra_model_request(self):
        fake = FakeCompletions([SimpleNamespace(role="assistant", content=None, tool_calls=[
            tool_call("call_1", "run_command", '{"command": "echo hello"}')])])
        with tempfile.TemporaryDirectory() as directory:
            result = run_agent(fake, "run", Path(directory), max_calls=1)
        self.assertEqual(result.exit_status, "call_limit")
        self.assertEqual(len(fake.requests), 1)


if __name__ == "__main__":
    unittest.main()
