import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import dispatch_tool


class ToolDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_directory.name)

    def tearDown(self):
        self.temp_directory.cleanup()

    def dispatch(self, name, arguments, timeout=3):
        return dispatch_tool(name, json.dumps(arguments), self.workspace, timeout)

    def python_command(self, source):
        return f'"{sys.executable}" -c "{source}"'

    def test_run_command_returns_output_for_success(self):
        result = self.dispatch("run_command", {
            "command": self.python_command("print('tool works')"),
        })

        self.assertTrue(result["ok"])
        self.assertEqual(result["returncode"], 0)
        self.assertFalse(result["timed_out"])
        self.assertIn("tool works", result["output"])

    def test_run_command_keeps_output_and_returncode_for_failure(self):
        result = self.dispatch("run_command", {
            "command": self.python_command("import sys; print('expected failure'); sys.exit(7)"),
        })

        self.assertFalse(result["ok"])
        self.assertEqual(result["returncode"], 7)
        self.assertFalse(result["timed_out"])
        self.assertIn("expected failure", result["output"])

    def test_run_command_reports_timeout(self):
        result = self.dispatch("run_command", {
            "command": self.python_command("import time; time.sleep(2)"),
        }, timeout=1)

        self.assertFalse(result["ok"])
        self.assertIsNone(result["returncode"])
        self.assertTrue(result["timed_out"])

    def test_rejects_invalid_json(self):
        result = dispatch_tool("run_command", "{not json", self.workspace, 3)

        self.assertFalse(result["ok"])
        self.assertIn("Invalid tool arguments JSON", result["error"])

    def test_rejects_unknown_tool(self):
        result = self.dispatch("delete_everything", {"command": "echo no"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "Unknown tool: delete_everything")

    def test_finish_task_rejects_empty_or_extra_arguments(self):
        empty_result = self.dispatch("finish_task", {"summary": ""})
        extra_result = self.dispatch("finish_task", {
            "summary": "done", "unexpected": True,
        })

        self.assertFalse(empty_result["ok"])
        self.assertIn("non-empty", empty_result["error"])
        self.assertFalse(extra_result["ok"])
        self.assertIn("exactly one argument", extra_result["error"])


if __name__ == "__main__":
    unittest.main()
