import tempfile
from pathlib import Path
import unittest

from ytmusic_organizer.setup_state import SetupState


class SetupRecoveryTests(unittest.TestCase):
    def test_setup_state_persists_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "setup_state.json"
            state = SetupState(path)
            state.mark_step("auth_ready")
            state.mark_step("liked_exported")

            reloaded = SetupState(path)
            self.assertTrue(reloaded.is_step_done("auth_ready"))
            self.assertTrue(reloaded.is_step_done("liked_exported"))
            self.assertFalse(reloaded.completed)

    def test_setup_state_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "setup_state.json"
            state = SetupState(path)
            state.complete()
            reloaded = SetupState(path)
            self.assertTrue(reloaded.completed)


if __name__ == "__main__":
    unittest.main()
