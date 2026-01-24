import os
import unittest
from unittest.mock import MagicMock, patch
from logic.implementor import Implementor
from data.db_manager import init_db, ACTIVITY_DB_PATH, TASK_DB_PATH


class TestRefactorSprint(unittest.TestCase):
    def setUp(self):
        # Ensure we use a clean test DB
        if os.path.exists(ACTIVITY_DB_PATH):
            os.remove(ACTIVITY_DB_PATH)
        if os.path.exists(TASK_DB_PATH):
            os.remove(TASK_DB_PATH)
        init_db()

        self.workspace_root = "."
        self.implementor = Implementor(workspace_root=self.workspace_root)

        # Set simulation mode for predictable tests
        os.environ["L4_SIMULATION"] = "true"

    def test_run_refactor_sprint_no_changes(self):
        # Mock LLM to return no changes
        self.implementor.llm.call_multi_file = MagicMock(
            return_value={"files": {}, "usage": {"total_tokens": 100}, "cost": 0.001}
        )

        result = self.implementor.run_refactor_sprint()
        self.assertTrue(result)
        self.implementor.llm.call_multi_file.assert_called_once()

    @patch("builtins.open", new_callable=unittest.mock.mock_open, read_data="content")
    @patch("os.path.exists", return_value=True)
    @patch("glob.glob", return_value=["v1/logic/utils.py", "v1/test_poc.py"])
    def test_run_refactor_sprint_with_changes(self, mock_glob, mock_exists, mock_open):
        # Mock LLM to return changes
        self.implementor.llm.call_multi_file = MagicMock(
            return_value={
                "files": {"v1/logic/utils.py": "new content"},
                "usage": {"total_tokens": 200},
                "cost": 0.002,
            }
        )

        # Mock Git commit
        self.implementor.git.commit = MagicMock(return_value=True)

        result = self.implementor.run_refactor_sprint()

        self.assertTrue(result)
        self.implementor.git.commit.assert_called_once()
        # Verify that it tried to commit ACT-200
        args, kwargs = self.implementor.git.commit.call_args
        self.assertEqual(args[0], "ACT-200")
        self.assertIn("v1/logic/utils.py", kwargs["files"])


if __name__ == "__main__":
    unittest.main()
