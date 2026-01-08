import datetime as dt
import tempfile
import unittest
from pathlib import Path

from dmi_radar_history.state import load_state, save_state, State


class TestState(unittest.TestCase):
    def test_state_roundtrip(self) -> None:
        state = State(last_times={"prectype": dt.datetime(2025, 1, 1, tzinfo=dt.timezone.utc)})
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            save_state(path, state)
            loaded = load_state(path)
        self.assertEqual(state.last_times["prectype"], loaded.last_times["prectype"])


if __name__ == "__main__":
    unittest.main()
