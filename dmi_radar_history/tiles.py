from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path

from .wms import BoundingBox, LayerInfo

DEFAULT_TILE_WIDTH = 512
DEFAULT_TILE_HEIGHT = 512
DEFAULT_TILE_BBOX = BoundingBox(
    crs="EPSG:3575",
    minx=85937.5,
    miny=-3808593.75,
    maxx=167968.75,
    maxy=-3726562.5,
)


@dataclasses.dataclass(frozen=True)
class TileRequest:
    bbox: BoundingBox
    width: int
    height: int


@dataclasses.dataclass(frozen=True)
class TileConfig:
    tile_width: int = DEFAULT_TILE_WIDTH
    tile_height: int = DEFAULT_TILE_HEIGHT
    resolution: float | None = None
    bboxes: tuple[BoundingBox, ...] | None = None


def load_tile_config(path: str | Path | None) -> TileConfig:
    if path is None:
        return TileConfig()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    tile_width = data.get("tile_width", DEFAULT_TILE_WIDTH)
    tile_height = data.get("tile_height", DEFAULT_TILE_HEIGHT)
    resolution = data.get("resolution")
    bboxes_data = data.get("bboxes")
    bboxes = None
    if bboxes_data:
        bboxes = tuple(
            BoundingBox(
                crs=bbox.get("crs", "EPSG:3575"),
                minx=bbox["minx"],
                miny=bbox["miny"],
                maxx=bbox["maxx"],
                maxy=bbox["maxy"],
            )
            for bbox in bboxes_data
        )
    return TileConfig(
        tile_width=tile_width,
        tile_height=tile_height,
        resolution=resolution,
        bboxes=bboxes,
    )


def resolve_tiles(layer: LayerInfo, config: TileConfig) -> list[TileRequest]:
    if config.bboxes:
        return [TileRequest(bbox=bbox, width=config.tile_width, height=config.tile_height) for bbox in config.bboxes]
    if config.resolution and layer.bbox:
        return _generate_tiles(layer.bbox, config.tile_width, config.tile_height, config.resolution)
    if layer.bbox:
        return [TileRequest(bbox=layer.bbox, width=config.tile_width, height=config.tile_height)]
    return [TileRequest(bbox=DEFAULT_TILE_BBOX, width=config.tile_width, height=config.tile_height)]


def _generate_tiles(
    bbox: BoundingBox,
    tile_width: int,
    tile_height: int,
    resolution: float,
) -> list[TileRequest]:
    tile_width_units = tile_width * resolution
    tile_height_units = tile_height * resolution
    tiles = []
    x_count = max(1, math.ceil(bbox.width / tile_width_units))
    y_count = max(1, math.ceil(bbox.height / tile_height_units))
    for x_index in range(x_count):
        minx = bbox.minx + x_index * tile_width_units
        maxx = minx + tile_width_units
        for y_index in range(y_count):
            miny = bbox.miny + y_index * tile_height_units
            maxy = miny + tile_height_units
            tiles.append(
                TileRequest(
                    bbox=BoundingBox(
                        crs=bbox.crs,
                        minx=minx,
                        miny=miny,
                        maxx=maxx,
                        maxy=maxy,
                    ),
                    width=tile_width,
                    height=tile_height,
                )
            )
    return tiles
