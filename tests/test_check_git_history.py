"""The history preflight must not mistake missing git or shallow history for a pass."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_git_history import check_history  # noqa: E402


class HistoryCheckTests(unittest.TestCase):
    def test_full_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", "-q", directory], check=True)
            ok, message = check_history(Path(directory))
        self.assertTrue(ok)
        self.assertIn("still require verification", message)

    def test_shallow_repository(self):
        with patch("check_git_history.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "true\n", "")
            ok, message = check_history(Path("."))
        self.assertFalse(ok)
        self.assertIn("git fetch --unshallow origin", message)

    def test_not_a_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            ok, message = check_history(Path(directory))
        self.assertFalse(ok)
        self.assertIn("Cannot check git history", message)

    def test_git_unavailable(self):
        with patch("check_git_history.subprocess.run", side_effect=FileNotFoundError("git")):
            ok, _ = check_history(Path("."))
        self.assertFalse(ok)

    def test_unknown_output_fails_closed(self):
        with patch("check_git_history.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "unknown\n", "")
            self.assertFalse(check_history(Path("."))[0])


if __name__ == "__main__":
    unittest.main()
