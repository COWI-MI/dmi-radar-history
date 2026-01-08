import unittest

from dmi_radar_history.tiles import TileConfig, resolve_tiles
from dmi_radar_history.wms import BoundingBox, LayerInfo


class TestTiles(unittest.TestCase):
    def test_resolve_tiles_defaults(self) -> None:
        layer = LayerInfo(
            name="test",
            title="Test",
            times=(),
            bbox=BoundingBox(crs="EPSG:3575", minx=0, miny=0, maxx=10, maxy=10),
        )
        config = TileConfig()
        tiles = resolve_tiles(layer, config)
        self.assertEqual(len(tiles), 1)
        self.assertEqual(tiles[0].bbox.minx, 0)

    def test_resolve_tiles_with_resolution(self) -> None:
        layer = LayerInfo(
            name="test",
            title="Test",
            times=(),
            bbox=BoundingBox(crs="EPSG:3575", minx=0, miny=0, maxx=1024, maxy=1024),
        )
        config = TileConfig(tile_width=512, tile_height=512, resolution=1.0)
        tiles = resolve_tiles(layer, config)
        self.assertEqual(len(tiles), 4)


if __name__ == "__main__":
    unittest.main()
