# Agent guidelines

- Keep changes focused and update tests when behavior changes.
- Prefer clear, standard-library-only Python additions unless dependencies are required.
- Run `pytest` when updating code paths covered by tests.

# Project notes

- Entry points:
  - Downloader: `python -m dmi_radar_history.downloader` (also `python -m dmi_radar_history`)
  - Daily stacker: `python -m dmi_radar_history.stacker`
  - Viewer: `python -m dmi_radar_history.viewer`
- Stacking/viewer require Pillow (`pip install pillow`).
- Stacker output lives under `daily/` with per-layer, per-day tiles and a `manifest.json` used by the viewer.
