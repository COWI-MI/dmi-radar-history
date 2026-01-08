from __future__ import annotations

import argparse
import datetime as dt
import logging
from pathlib import Path
import urllib.request

from .state import State, load_state, save_state
from .tiles import TileRequest, load_tile_config, resolve_tiles
from .wms import build_getmap_url, fetch_capabilities, parse_capabilities

LOGGER = logging.getLogger(__name__)
DEFAULT_CAPABILITIES_URL = "https://www.dmi.dk/ZoombareKort/map?REQUEST=GetCapabilities"
DEFAULT_BASE_URL = "https://www.dmi.dk/ZoombareKort/map"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _download_tile(url: str, destination: Path, timeout: float) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "dmi-radar-history/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content = response.read()
    destination.write_bytes(content)


def _tile_filename(tile: TileRequest, index: int) -> str:
    bbox = tile.bbox
    return f"tile_{index}_{bbox.minx}_{bbox.miny}_{bbox.maxx}_{bbox.maxy}.png"


def _filter_recent(times: list[dt.datetime], max_age_hours: float | None) -> list[dt.datetime]:
    if max_age_hours is None:
        return times
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=max_age_hours)
    return [time for time in times if time >= cutoff]


def _process_layer(
    layer,
    base_url: str,
    tile_requests: list[TileRequest],
    output_dir: Path,
    state: State,
    timeout: float,
    max_age_hours: float | None,
    dry_run: bool,
) -> None:
    times = list(layer.times)
    times.sort()
    times = _filter_recent(times, max_age_hours)
    last_saved = state.latest_for(layer.name)
    for time_value in times:
        if last_saved and time_value <= last_saved:
            continue
        time_dir = output_dir / layer.name / time_value.strftime("%Y%m%dT%H%M%SZ")
        _ensure_dir(time_dir)
        missing_tiles: list[tuple[int, TileRequest, Path]] = []
        for index, tile in enumerate(tile_requests):
            filename = _tile_filename(tile, index)
            target = time_dir / filename
            if target.exists():
                continue
            missing_tiles.append((index, tile, target))
        if not missing_tiles:
            state.update(layer.name, time_value)
            continue
        if dry_run:
            for index, tile, _target in missing_tiles:
                url = build_getmap_url(
                    base_url=base_url,
                    layer=layer.name,
                    time_value=time_value,
                    bbox=tile.bbox,
                    width=tile.width,
                    height=tile.height,
                )
                LOGGER.info("Would fetch %s", url)
            continue
        for index, tile, target in missing_tiles:
            url = build_getmap_url(
                base_url=base_url,
                layer=layer.name,
                time_value=time_value,
                bbox=tile.bbox,
                width=tile.width,
                height=tile.height,
            )
            LOGGER.info("Fetching %s", url)
            _download_tile(url, target, timeout)
        state.update(layer.name, time_value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Save DMI radar WMS tiles.")
    parser.add_argument("--capabilities-url", default=DEFAULT_CAPABILITIES_URL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output-dir", default="data")
    parser.add_argument("--state-file", default=None)
    parser.add_argument("--tile-config", default=None)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-age-hours", type=float, default=12.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    capabilities_xml = fetch_capabilities(args.capabilities_url, timeout=args.timeout)
    layers = parse_capabilities(capabilities_xml)
    tile_config = load_tile_config(args.tile_config)

    output_dir = Path(args.output_dir)
    state_file = Path(args.state_file) if args.state_file else output_dir / "state.json"
    state = load_state(state_file)

    for layer in layers:
        if not layer.times:
            continue
        tiles = resolve_tiles(layer, tile_config)
        _process_layer(
            layer=layer,
            base_url=args.base_url,
            tile_requests=tiles,
            output_dir=output_dir,
            state=state,
            timeout=args.timeout,
            max_age_hours=args.max_age_hours,
            dry_run=args.dry_run,
        )

    if not args.dry_run:
        save_state(state_file, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
