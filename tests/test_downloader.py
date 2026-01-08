from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import urllib.request

import pytest

from dmi_radar_history.downloader import _download_tile


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
