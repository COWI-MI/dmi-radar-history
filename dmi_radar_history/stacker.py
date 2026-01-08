from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, cast

LOGGER = logging.getLogger(__name__)

_TIME_DIR_RE = re.compile(r"^\d{8}T\d{6}Z$")
_TILE_NAME_RE = re.compile(r"^tile_(\d+)_.*\.png$")

if TYPE_CHECKING:
    from PIL.Image import Image as PILImageClass

    ImageType = PILImageClass
else:
    ImageType = object

try:
    from PIL import Image as PILImage
    from PIL import ImageChops as PILImageChops
except ModuleNotFoundError:  # pragma: no cover - exercised in runtime environments without Pillow
    PILImage = None
    PILImageChops = None


def _require_pillow() -> tuple[Any, Any]:
    if PILImage is None or PILImageChops is None:
        raise RuntimeError("Pillow is required to stack images. Install with: pip install pillow")
    return cast(Any, PILImage), cast(Any, PILImageChops)


def _compute_chroma(chops: Any, image: ImageType) -> Any:
    r, g, b = image.convert("RGB").split()
    max_rg = chops.lighter(r, g)
    max_rgb = chops.lighter(max_rg, b)
    min_rg = chops.darker(r, g)
    min_rgb = chops.darker(min_rg, b)
    return chops.subtract(max_rgb, min_rgb)


def _parse_time_dir(name: str) -> dt.datetime | None:
    if not _TIME_DIR_RE.match(name):
        return None
    parsed = dt.datetime.strptime(name, "%Y%m%dT%H%M%SZ")
    return parsed.replace(tzinfo=dt.timezone.utc)


def _parse_tile_index(filename: str) -> int | None:
    match = _TILE_NAME_RE.match(filename)
    if not match:
        return None
    return int(match.group(1))


def _iter_layer_dirs(input_dir: Path, layers: set[str] | None) -> Iterable[Path]:
    for entry in sorted(input_dir.iterdir()):
        if not entry.is_dir():
            continue
        if layers and entry.name not in layers:
            continue
        yield entry


def collect_day_tiles(
    input_dir: Path,
    layers: set[str] | None = None,
) -> dict[str, dict[dt.date, dict[int, list[tuple[dt.datetime, Path]]]]]:
    tiles: dict[str, dict[dt.date, dict[int, list[tuple[dt.datetime, Path]]]]] = {}
    for layer_dir in _iter_layer_dirs(input_dir, layers):
        layer = layer_dir.name
        for time_dir in sorted(layer_dir.iterdir()):
            if not time_dir.is_dir():
                continue
            time_value = _parse_time_dir(time_dir.name)
            if time_value is None:
                continue
            day = time_value.date()
            for tile_path in sorted(time_dir.glob("tile_*.png")):
                index = _parse_tile_index(tile_path.name)
                if index is None:
                    continue
                tiles.setdefault(layer, {}).setdefault(day, {}).setdefault(index, []).append((time_value, tile_path))
    return tiles


def _stack_images(paths: list[Path]) -> ImageType:
    pil, chops = _require_pillow()
    if not paths:
        raise ValueError("No images provided for stacking.")
    with pil.open(paths[0]) as img:
        base = img.convert("RGBA")
    base_chroma = _compute_chroma(chops, base)
    output = base.copy()
    for path in paths[1:]:
        with pil.open(path) as img:
            frame = img.convert("RGBA")
        if frame.size != base.size:
            raise ValueError(f"Mismatched tile sizes while stacking: {path}")
        frame_chroma = _compute_chroma(chops, frame)
        diff = chops.subtract(frame_chroma, base_chroma)
        mask = diff.point(lambda value: 255 if value > 18 else 0)
        output = pil.composite(frame, output, mask)
    return output


def build_day_stacks(
    input_dir: Path,
    output_dir: Path,
    layers: set[str] | None = None,
) -> dict:
    tiles = collect_day_tiles(input_dir, layers=layers)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "layers": [],
    }

    if not tiles:
        LOGGER.warning("No tiles discovered under %s", input_dir)
        return manifest

    for layer in sorted(tiles.keys()):
        layer_entry = {"name": layer, "days": []}
        for day in sorted(tiles[layer].keys()):
            day_tiles = tiles[layer][day]
            day_entry = {
                "date": day.isoformat(),
                "tiles": [],
                "times": [],
            }
            day_times = sorted({time for entries in day_tiles.values() for time, _ in entries})
            day_entry["times"] = [time.strftime("%Y-%m-%dT%H:%M:%SZ") for time in day_times]
            for index in sorted(day_tiles.keys()):
                entries = sorted(day_tiles[index], key=lambda item: item[0])
                paths = [path for _time, path in entries]
                stacked = _stack_images(paths)
                day_dir = output_dir / layer / day.isoformat()
                day_dir.mkdir(parents=True, exist_ok=True)
                output_path = day_dir / f"tile_{index}.png"
                stacked.save(output_path, format="PNG")
                rel_path = output_path.relative_to(output_dir).as_posix()
                day_entry["tiles"].append(
                    {
                        "index": index,
                        "path": rel_path,
                        "width": stacked.width,
                        "height": stacked.height,
                        "count": len(paths),
                    }
                )
            layer_entry["days"].append(day_entry)
        manifest["layers"].append(layer_entry)
    return manifest


def write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Stack radar tiles into daily composites.")
    parser.add_argument("--input-dir", default="data")
    parser.add_argument("--output-dir", default="daily")
    parser.add_argument("--manifest", default=None)
    parser.add_argument(
        "--layers",
        default="",
        help="Comma-separated layer names to include (default: all layers found).",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    layers = {name.strip() for name in args.layers.split(",") if name.strip()} or None

    manifest = build_day_stacks(input_dir, output_dir, layers=layers)
    manifest_path = Path(args.manifest) if args.manifest else output_dir / "manifest.json"
    write_manifest(manifest_path, manifest)
    LOGGER.info("Wrote manifest to %s", manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
