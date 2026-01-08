from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def render_viewer_html(manifest: dict, title: str = "Daily Precipitation Stack") -> str:
    manifest_json = json.dumps(manifest)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <style>
      :root {{
        color-scheme: light;
        --ink: #1e2d2b;
        --muted: #5a6b69;
        --accent: #e07a5f;
        --accent-soft: #f2cc8f;
        --panel: rgba(255, 255, 255, 0.9);
        --shadow: 0 14px 30px rgba(30, 45, 43, 0.12);
      }}
      * {{
        box-sizing: border-box;
      }}
      body {{
        margin: 0;
        font-family: "Fira Sans", "Trebuchet MS", "Segoe UI", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, #f2efe9 0%, #ece4d8 38%, #e7ddcc 70%),
          repeating-linear-gradient(135deg, rgba(255, 255, 255, 0.35), rgba(255, 255, 255, 0.35) 12px, transparent 12px, transparent 24px);
        min-height: 100vh;
        padding: 24px;
        display: flex;
        flex-direction: column;
        --viewer-available-height: calc(100vh - 220px);
      }}
      header {{
        display: flex;
        flex-wrap: wrap;
        align-items: flex-end;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 24px;
      }}
      .title {{
        font-family: "Palatino Linotype", "Book Antiqua", Palatino, serif;
        font-size: clamp(1.8rem, 3vw, 2.6rem);
        margin: 0;
      }}
      .subtitle {{
        margin: 4px 0 0;
        color: var(--muted);
      }}
      .panel {{
        background: var(--panel);
        border-radius: 16px;
        padding: 18px;
        box-shadow: var(--shadow);
        backdrop-filter: blur(6px);
      }}
      .controls {{
        display: grid;
        gap: 12px;
        min-width: 260px;
      }}
      .controls.inline {{
        display: flex;
        gap: 12px;
        align-items: end;
        justify-content: flex-end;
        min-width: auto;
        flex-wrap: wrap;
      }}
      label {{
        font-size: 0.9rem;
        color: var(--muted);
        display: block;
        margin-bottom: 6px;
      }}
      select {{
        width: 100%;
        padding: 10px 12px;
        border-radius: 10px;
        border: 1px solid #d6c8b7;
        background: #fffaf3;
        font-size: 1rem;
      }}
      main {{
        display: grid;
        gap: 16px;
        flex: 1 1 auto;
        min-height: 0;
      }}
      .meta {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
        color: var(--muted);
        font-size: 0.95rem;
      }}
      #metaRow {{
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        justify-content: space-between;
        align-items: center;
      }}
      .badge {{
        background: var(--accent-soft);
        color: #5b4028;
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 0.85rem;
      }}
      .tile-grid {{
        display: grid;
        gap: 18px;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        align-items: start;
      }}
      .tile-card {{
        background: #fff;
        border-radius: 18px;
        padding: 16px;
        box-shadow: 0 10px 20px rgba(30, 45, 43, 0.12);
        animation: floatIn 0.6s ease both;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }}
      .tile-card img {{
        width: 100%;
        border-radius: 12px;
        border: 1px solid #e5d8c8;
        display: block;
        height: auto;
        object-fit: contain;
        max-height: var(--viewer-available-height);
      }}
      @media (min-width: 900px) {{
        main {{
          grid-template-rows: auto 1fr;
        }}
        .tile-grid {{
          overflow: auto;
          padding-right: 6px;
        }}
      }}
      @media (max-height: 700px) {{
        body {{
          padding: 16px;
          --viewer-available-height: calc(100vh - 180px);
        }}
        header {{
          margin-bottom: 16px;
        }}
      }}
      @media (max-width: 720px) {{
        .controls.inline {{
          width: 100%;
          justify-content: flex-start;
        }}
      }}
      .tile-caption {{
        margin-top: 10px;
        font-size: 0.9rem;
        color: var(--muted);
      }}
      .empty {{
        padding: 40px;
        text-align: center;
        color: var(--muted);
        font-size: 1rem;
      }}
      @keyframes floatIn {{
        from {{
          opacity: 0;
          transform: translateY(12px);
        }}
        to {{
          opacity: 1;
          transform: translateY(0);
        }}
      }}
    </style>
  </head>
  <body>
    <header>
      <div>
        <h1 class="title">{title}</h1>
        <p class="subtitle">Daily composites built from radar frames so precipitation footprints stand out.</p>
      </div>
    </header>
    <main class="panel">
      <div class="meta" id="metaRow">
        <div class="meta" id="meta"></div>
        <div class="controls inline">
          <div>
            <label for="layerSelect">Layer</label>
            <select id="layerSelect"></select>
          </div>
          <div>
            <label for="daySelect">Day</label>
            <select id="daySelect"></select>
          </div>
        </div>
      </div>
      <div class="tile-grid" id="tiles"></div>
      <div class="empty" id="emptyState" hidden>No stacked tiles found. Run the stacker first.</div>
    </main>
    <script>
      const manifest = {manifest_json};
      const layerSelect = document.getElementById("layerSelect");
      const daySelect = document.getElementById("daySelect");
      const tilesEl = document.getElementById("tiles");
      const metaEl = document.getElementById("meta");
      const emptyEl = document.getElementById("emptyState");

      function formatCount(label, value) {{
        return `<span class="badge">${{label}}: ${{value}}</span>`;
      }}

      function loadLayers() {{
        layerSelect.innerHTML = "";
        (manifest.layers || []).forEach((layer) => {{
          const option = document.createElement("option");
          option.value = layer.name;
          option.textContent = layer.name;
          layerSelect.appendChild(option);
        }});
      }}

      function loadDays(layer) {{
        daySelect.innerHTML = "";
        layer.days.forEach((day) => {{
          const option = document.createElement("option");
          option.value = day.date;
          option.textContent = day.date;
          daySelect.appendChild(option);
        }});
      }}

      function renderTiles(layer, day) {{
        tilesEl.innerHTML = "";
        metaEl.innerHTML = "";
        if (!day || day.tiles.length === 0) {{
          emptyEl.hidden = false;
          return;
        }}
        emptyEl.hidden = true;
        const timeCount = day.times ? day.times.length : 0;
        metaEl.innerHTML = [
          formatCount("Tiles", day.tiles.length),
          formatCount("Frames", timeCount),
          formatCount("Layer", layer.name),
          formatCount("Day", day.date),
        ].join("");
        day.tiles.forEach((tile) => {{
          const card = document.createElement("div");
          card.className = "tile-card";
          const img = document.createElement("img");
          img.src = tile.path;
          img.alt = `Tile ${{tile.index}}`;
          const caption = document.createElement("div");
          caption.className = "tile-caption";
          caption.textContent = `Tile ${{tile.index}} | ${{tile.width}}x${{tile.height}} px | ${{tile.count}} frames`;
          card.appendChild(img);
          card.appendChild(caption);
          tilesEl.appendChild(card);
        }});
      }}

      function render() {{
        const layer = (manifest.layers || []).find((item) => item.name === layerSelect.value);
        if (!layer) {{
          emptyEl.hidden = false;
          tilesEl.innerHTML = "";
          metaEl.innerHTML = "";
          return;
        }}
        const day = layer.days.find((item) => item.date === daySelect.value);
        renderTiles(layer, day);
      }}

      function init() {{
        if (!manifest.layers || manifest.layers.length === 0) {{
          emptyEl.hidden = false;
          return;
        }}
        loadLayers();
        const firstLayer = manifest.layers[0];
        loadDays(firstLayer);
        layerSelect.value = firstLayer.name;
        daySelect.value = firstLayer.days[0]?.date || "";
        render();
        layerSelect.addEventListener("change", () => {{
          const layer = manifest.layers.find((item) => item.name === layerSelect.value);
          if (!layer) {{
            return;
          }}
          loadDays(layer);
          daySelect.value = layer.days[0]?.date || "";
          render();
        }});
        daySelect.addEventListener("change", render);
      }}

      init();
    </script>
  </body>
</html>
"""


def write_viewer(output_dir: Path, manifest: dict, title: str = "Daily Precipitation Stack") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "index.html"
    path.write_text(render_viewer_html(manifest, title=title), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an HTML viewer for stacked daily tiles.")
    parser.add_argument("--stacked-dir", default="daily")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--title", default="Daily Precipitation Stack")
    args = parser.parse_args()

    stacked_dir = Path(args.stacked_dir)
    manifest_path = Path(args.manifest) if args.manifest else stacked_dir / "manifest.json"
    output_dir = Path(args.output_dir) if args.output_dir else stacked_dir
    manifest = load_manifest(manifest_path)
    write_viewer(output_dir, manifest, title=args.title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
