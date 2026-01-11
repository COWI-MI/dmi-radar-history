from __future__ import annotations

import datetime as dt
from pathlib import Path
from types import SimpleNamespace
import urllib.request

import pytest

from dmi_radar_history.downloader import _download_tile, _process_layer
from dmi_radar_history.state import State
from dmi_radar_history.tiles import TileRequest
from dmi_radar_history.wms import BoundingBox


class _FakeResponse:
    def __init__(self, body: bytes, content_type: str) -> None:
        self._body = body
        self.headers = SimpleNamespace(get=lambda key, default=None: content_type if key == "Content-Type" else default)

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_download_tile_rejects_non_image(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_urlopen(_request: urllib.request.Request, timeout: float = 0) -> _FakeResponse:
        return _FakeResponse(b"not an image", "text/html")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    destination = tmp_path / "tile.png"

    with pytest.raises(ValueError, match="Unexpected content type"):
        _download_tile("https://example.invalid", destination, timeout=1.0)
    assert not destination.exists()


def test_download_tile_writes_image(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

    def fake_urlopen(_request: urllib.request.Request, timeout: float = 0) -> _FakeResponse:
        return _FakeResponse(png_bytes, "image/png")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    destination = tmp_path / "tile.png"

    _download_tile("https://example.invalid", destination, timeout=1.0)

    assert destination.read_bytes() == png_bytes


def test_process_layer_stops_after_failed_timestamp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[str] = []

    def fake_download(url: str, destination: Path, timeout: float) -> None:
        calls.append(url)
        raise RuntimeError("boom")

    monkeypatch.setattr("dmi_radar_history.downloader._download_tile", fake_download)

    times = (
        dt.datetime(2024, 1, 1, 0, 0, tzinfo=dt.timezone.utc),
        dt.datetime(2024, 1, 1, 0, 10, tzinfo=dt.timezone.utc),
    )
    layer = SimpleNamespace(name="layer", times=times)
    tile_requests = [
        TileRequest(
            bbox=BoundingBox(crs="EPSG:3575", minx=0, miny=0, maxx=1, maxy=1),
            width=1,
            height=1,
        )
    ]
    state = State(last_times={})

    _process_layer(
        layer=layer,
        base_url="https://example.invalid",
        tile_requests=tile_requests,
        output_dir=tmp_path,
        state=state,
        timeout=1.0,
        max_age_hours=None,
        dry_run=False,
    )

    assert len(calls) == 1
    assert state.latest_for("layer") is None
