from __future__ import annotations

import dataclasses
import datetime as dt
import json
from pathlib import Path


def _parse_time(value: str) -> dt.datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def _format_time(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclasses.dataclass
class State:
    last_times: dict[str, dt.datetime]

    def latest_for(self, layer: str) -> dt.datetime | None:
        return self.last_times.get(layer)

    def update(self, layer: str, value: dt.datetime) -> None:
        current = self.last_times.get(layer)
        if current is None or value > current:
            self.last_times[layer] = value

    def to_dict(self) -> dict[str, str]:
        return {layer: _format_time(value) for layer, value in self.last_times.items()}


def load_state(path: str | Path) -> State:
    path = Path(path)
    if not path.exists():
        return State(last_times={})
    data = json.loads(path.read_text(encoding="utf-8"))
    last_times = {layer: _parse_time(value) for layer, value in data.items()}
    return State(last_times=last_times)


def save_state(path: str | Path, state: State) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
