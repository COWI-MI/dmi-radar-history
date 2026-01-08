# dmi-radar-history

Utilities for downloading historical radar tiles from the Danish Meteorological Institute (DMI) WMS service.

## Features

- Fetches radar layers listed in the DMI WMS capabilities document.
- Saves timestamped tiles to disk and tracks progress in a local state file.
- Supports configurable tile sizing and tiling schemes via JSON.

## Requirements

- Python 3.10+
- No third-party runtime dependencies

## Quickstart

```bash
python -m dmi_radar_history --output-dir data --max-age-hours 6
```

The command above will fetch the most recent tiles (up to six hours old) and store them under `data/`.
A `state.json` file is created in the same directory to track the latest saved timestamps per layer.

### Common options

- `--dry-run`: log the URLs that would be downloaded without saving files.
- `--tile-config path/to/tiles.json`: specify tile sizing, resolution, or bounding boxes.
- `--state-file path/to/state.json`: use a custom state file location.

### Tile configuration

Create a JSON file when you want to control the tile size, the resolution, or supply explicit bounding boxes:

```json
{
  "tile_width": 512,
  "tile_height": 512,
  "resolution": 500.0,
  "bboxes": [
    {"crs": "EPSG:3575", "minx": 85937.5, "miny": -3808593.75, "maxx": 167968.75, "maxy": -3726562.5}
  ]
}
```

When both `resolution` and `bboxes` are omitted, a single tile is generated for each layer using the
layer bounding box (or a fallback default).

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip pytest
pytest
```

## Project layout

- `dmi_radar_history/`: application source.
- `tests/`: pytest test suite.
```
