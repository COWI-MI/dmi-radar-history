from pathlib import Path
import threading
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from dmi_radar_history import viewer


def _sample_manifest() -> dict:
    return {
        "generated_at": "2026-01-08T00:00:00Z",
        "layers": [
            {
                "name": "prectype",
                "days": [
                    {
                        "date": "2025-01-01",
                        "times": ["2025-01-01T00:00:00Z"],
                        "tiles": [
                            {
                                "index": 0,
                                "path": "prectype/2025-01-01/tile_0.png",
                                "width": 512,
                                "height": 512,
                                "count": 1,
                            }
                        ],
                    }
                ],
            }
        ],
    }


def _sample_manifest_multiple_days() -> dict:
    return {
        "generated_at": "2026-01-08T00:00:00Z",
        "layers": [
            {
                "name": "prectype",
                "days": [
                    {
                        "date": "2025-01-01",
                        "times": ["2025-01-01T00:00:00Z"],
                        "tiles": [
                            {
                                "index": 0,
                                "path": "prectype/2025-01-01/tile_0.png",
                                "width": 512,
                                "height": 512,
                                "count": 1,
                            }
                        ],
                    },
                    {
                        "date": "2025-01-02",
                        "times": ["2025-01-02T00:00:00Z"],
                        "tiles": [
                            {
                                "index": 0,
                                "path": "prectype/2025-01-02/tile_0.png",
                                "width": 512,
                                "height": 512,
                                "count": 1,
                            }
                        ],
                    },
                ],
            }
        ],
    }


def test_render_viewer_html_embeds_manifest() -> None:
    html = viewer.render_viewer_html(_sample_manifest(), title="Test Viewer", tile_base_path="daily")
    assert "Test Viewer" in html
    assert '"layers"' in html
    assert "prectype" in html
    assert "tile_0.png" in html
    assert "daily/" in html


def test_render_viewer_html_supports_multiple_days() -> None:
    html = viewer.render_viewer_html(_sample_manifest_multiple_days(), title="Test Viewer", tile_base_path="daily")
    assert "2025-01-01" in html
    assert "2025-01-02" in html
    assert "option.value = String(index)" in html
    assert "const day = getSelectedDay(layer);" in html


def test_write_viewer_creates_file(tmp_path: Path) -> None:
    manifest = _sample_manifest()
    output = viewer.write_viewer(tmp_path, manifest, title="Viewer", tile_base_path="daily")
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "Viewer" in content
    assert "prectype" in content
    assert "daily/" in content


def test_viewer_page_is_reachable(tmp_path: Path) -> None:
    manifest = _sample_manifest()
    viewer.write_viewer(tmp_path, manifest, title="Viewer Page", tile_base_path="daily")

    handler = lambda *args, **kwargs: SimpleHTTPRequestHandler(*args, directory=str(tmp_path), **kwargs)
    server = ThreadingHTTPServer(("localhost", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://localhost:{server.server_port}/index.html"
        with urllib.request.urlopen(url) as response:
            body = response.read().decode("utf-8")
        assert "Viewer Page" in body
        assert "tile_0.png" in body
    finally:
        server.shutdown()
        thread.join()
