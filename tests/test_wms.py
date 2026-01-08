import datetime as dt
from pathlib import Path
import unittest

from dmi_radar_history.wms import build_getmap_url, parse_capabilities


class TestWmsCapabilities(unittest.TestCase):
    def test_parse_capabilities_layers(self) -> None:
        xml_text = Path("tests/fixtures/capabilities.xml").read_text(encoding="utf-8")
        layers = parse_capabilities(xml_text)
        names = {layer.name for layer in layers}
        self.assertEqual(names, {"prectype", "reflectivity", "daily"})
        prectype = next(layer for layer in layers if layer.name == "prectype")
        self.assertEqual(len(prectype.times), 2)
        self.assertEqual(prectype.bbox.crs, "EPSG:3575")
        reflectivity = next(layer for layer in layers if layer.name == "reflectivity")
        self.assertEqual(len(reflectivity.times), 3)
        daily = next(layer for layer in layers if layer.name == "daily")
        self.assertEqual(len(daily.times), 3)
        self.assertEqual(daily.times[0].date().isoformat(), "2025-01-01")

    def test_build_getmap_url(self) -> None:
        xml_text = Path("tests/fixtures/capabilities.xml").read_text(encoding="utf-8")
        layer = parse_capabilities(xml_text)[0]
        time_value = dt.datetime(2025, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        url = build_getmap_url(
            base_url="https://example.com/map",
            layer=layer.name,
            time_value=time_value,
            bbox=layer.bbox,
            width=512,
            height=512,
        )
        self.assertIn("REQUEST=GetMap", url)
        self.assertIn("LAYERS=prectype", url)
        self.assertIn("TIME=2025-01-01T00%3A00%3A00Z", url)


if __name__ == "__main__":
    unittest.main()
