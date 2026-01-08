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
    minx=-132072.7784,
    miny=-3912803.2510,
    maxx=360255.4228,
    maxy=-3547098.2575,
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
    extent = _select_extent(layer.bbox)
    if config.resolution:
        return _generate_tiles(extent, config.tile_width, config.tile_height, config.resolution)
    return [TileRequest(bbox=extent, width=config.tile_width, height=config.tile_height)]


def _select_extent(layer_bbox: BoundingBox | None) -> BoundingBox:
    if layer_bbox is None:
        return DEFAULT_TILE_BBOX
    if layer_bbox.crs.upper() != DEFAULT_TILE_BBOX.crs.upper():
        return layer_bbox
    if _contains_bbox(layer_bbox, DEFAULT_TILE_BBOX):
        return DEFAULT_TILE_BBOX
    return layer_bbox


def _contains_bbox(outer: BoundingBox, inner: BoundingBox) -> bool:
    return (
        outer.minx <= inner.minx
        and outer.miny <= inner.miny
        and outer.maxx >= inner.maxx
        and outer.maxy >= inner.maxy
    )


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
