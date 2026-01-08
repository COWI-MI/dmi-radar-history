import datetime as dt
from pathlib import Path

from PIL import Image

from dmi_radar_history.stacker import _parse_tile_index, _parse_time_dir, build_day_stacks


def _write_tile(path: Path, pixel: tuple[int, int], color: tuple[int, int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
    image.putpixel(pixel, color)
    image.save(path, format="PNG")


def test_build_day_stacks_creates_composite(tmp_path: Path) -> None:
    input_dir = tmp_path / "data"
    output_dir = tmp_path / "daily"
    time_one = input_dir / "prectype" / "20250101T000000Z"
    time_two = input_dir / "prectype" / "20250101T120000Z"
    _write_tile(time_one / "tile_0_0_0_1_1.png", (0, 0), (255, 0, 0, 255))
    _write_tile(time_two / "tile_0_0_0_1_1.png", (1, 1), (0, 0, 255, 255))

    manifest = build_day_stacks(input_dir, output_dir)

    stacked = output_dir / "prectype" / "2025-01-01" / "tile_0.png"
    assert stacked.exists()
    with Image.open(stacked) as image:
        image = image.convert("RGBA")
        assert image.getpixel((0, 0)) == (255, 0, 0, 255)
        assert image.getpixel((1, 1)) == (0, 0, 255, 255)
        assert image.getpixel((1, 0))[3] == 0
    day = manifest["layers"][0]["days"][0]
    assert day["date"] == "2025-01-01"
    assert day["tiles"][0]["path"] == "prectype/2025-01-01/tile_0.png"


def test_parse_helpers() -> None:
    parsed = _parse_time_dir("20250101T000000Z")
    assert parsed is not None
    assert parsed.date() == dt.date(2025, 1, 1)
    assert _parse_time_dir("nope") is None
    assert _parse_tile_index("tile_2_0_0_1_1.png") == 2
    assert _parse_tile_index("tile_no_index.png") is None
