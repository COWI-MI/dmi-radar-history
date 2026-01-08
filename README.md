# dmi-radar-history

Utilities for downloading historical radar tiles from the Danish Meteorological Institute (DMI) WMS service.

## Features

- Fetches radar layers listed in the DMI WMS capabilities document.
- Saves timestamped tiles to disk and tracks progress in a local state file.
- Supports configurable tile sizing and tiling schemes via JSON.

## Requirements

- Python 3.10+
- Pillow (required for stacking/viewer features)

## Quickstart

```bash
python -m dmi_radar_history.downloader --output-dir data --max-age-hours 6
```

The command above will fetch the most recent tiles (up to six hours old) and store them under `data/`.
A `state.json` file is created in the same directory to track the latest saved timestamps per layer.

You can also use `python -m dmi_radar_history` as a shortcut to the downloader.

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
    {"crs": "EPSG:3575", "minx": -132072.7784, "miny": -3912803.2510, "maxx": 360255.4228, "maxy": -3547098.2575}
  ]
}
```

When both `resolution` and `bboxes` are omitted, a single tile is generated for each layer using the
Denmark extent for EPSG:3575 layers (falling back to the layer bounding box when it doesn't cover Denmark).

## Daily stack + viewer

Stack a day's worth of frames into a single composite per tile:

```bash
python -m dmi_radar_history.stacker --input-dir data --output-dir daily
```

Generate a static HTML viewer for the stacked output:

```bash
python -m dmi_radar_history.viewer --stacked-dir daily
```

Open `daily/index.html` to browse per-day composites.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip pytest pillow
pytest
```

## Project layout

- `dmi_radar_history/`: application source.
- `tests/`: pytest test suite.
```
