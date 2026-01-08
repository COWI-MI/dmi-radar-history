from __future__ import annotations

import dataclasses
import datetime as dt
import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class BoundingBox:
    crs: str
    minx: float
    miny: float
    maxx: float
    maxy: float

    @property
    def width(self) -> float:
        return self.maxx - self.minx

    @property
    def height(self) -> float:
        return self.maxy - self.miny


@dataclasses.dataclass(frozen=True)
class LayerInfo:
    name: str
    title: str
    times: tuple[dt.datetime, ...]
    bbox: BoundingBox | None


def _strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_time_value(value: str) -> list[dt.datetime]:
    value = value.strip()
    if not value:
        return []
    if "/" in value:
        parts = value.split("/")
        if len(parts) == 3:
            start = _parse_time(parts[0])
            end = _parse_time(parts[1])
            step = _parse_duration(parts[2])
            if step is None:
                return []
            times = []
            current = start
            while current <= end:
                times.append(current)
                current += step
            return times
    times = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        times.append(_parse_time(item))
    return times


def _parse_time(value: str) -> dt.datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def _parse_duration(value: str) -> dt.timedelta | None:
    if not value.startswith("P"):
        return None
    date_part = value[1:]
    time_part = ""
    if "T" in date_part:
        date_part, time_part = date_part.split("T", 1)

    def parse_segment(segment: str, designator: str) -> int:
        if designator not in segment:
            return 0
        number = ""
        for char in segment:
            if char.isdigit():
                number += char
            elif char == designator:
                break
            else:
                number = ""
        return int(number) if number else 0

    years = parse_segment(date_part, "Y")
    months = parse_segment(date_part, "M")
    weeks = parse_segment(date_part, "W")
    days = parse_segment(date_part, "D")
    hours = parse_segment(time_part, "H")
    minutes = parse_segment(time_part, "M")
    seconds = parse_segment(time_part, "S")

    if years or months:
        return None
    total_days = days + weeks * 7
    return dt.timedelta(
        days=total_days,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
    )


def fetch_capabilities(url: str, timeout: float = 20.0) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "dmi-radar-history/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def parse_capabilities(xml_text: str) -> list[LayerInfo]:
    root = ET.fromstring(xml_text)
    layers = []
    for layer in root.iter():
        if _strip_namespace(layer.tag) != "Layer":
            continue
        name_el = layer.find("./{*}Name")
        if name_el is None or not name_el.text:
            continue
        title_el = layer.find("./{*}Title")
        title = title_el.text.strip() if title_el is not None and title_el.text else name_el.text
        time_values = []
        for dim in layer.findall("./{*}Dimension"):
            name = dim.attrib.get("name", "").lower()
            if name == "time" and dim.text:
                time_values.extend(_parse_time_value(dim.text))
        for extent in layer.findall("./{*}Extent"):
            name = extent.attrib.get("name", "").lower()
            if name == "time" and extent.text:
                time_values.extend(_parse_time_value(extent.text))
        bbox = _find_bbox(layer)
        if not time_values:
            LOGGER.debug("No time dimension found for layer %s", name_el.text)
        layers.append(
            LayerInfo(
                name=name_el.text.strip(),
                title=title,
                times=tuple(sorted(set(time_values))),
                bbox=bbox,
            )
        )
    return layers


def _find_bbox(layer: ET.Element) -> BoundingBox | None:
    candidates = []
    for bbox in layer.findall("./{*}BoundingBox"):
        crs = bbox.attrib.get("SRS") or bbox.attrib.get("CRS")
        if not crs:
            continue
        candidates.append((crs, bbox))
    preferred = None
    for crs, bbox in candidates:
        if crs.upper() == "EPSG:3575":
            preferred = bbox
            crs_value = crs
            break
    else:
        if candidates:
            crs_value, preferred = candidates[0]
        else:
            return None
    return BoundingBox(
        crs=crs_value,
        minx=float(preferred.attrib["minx"]),
        miny=float(preferred.attrib["miny"]),
        maxx=float(preferred.attrib["maxx"]),
        maxy=float(preferred.attrib["maxy"]),
    )


def build_getmap_url(
    base_url: str,
    layer: str,
    time_value: dt.datetime,
    bbox: BoundingBox,
    width: int,
    height: int,
) -> str:
    params = {
        "REQUEST": "GetMap",
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "FORMAT": "image/png",
        "STYLES": "",
        "TRANSPARENT": "true",
        "TIME": time_value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "LAYERS": layer,
        "WIDTH": str(width),
        "HEIGHT": str(height),
        "SRS": bbox.crs,
        "BBOX": f"{bbox.minx},{bbox.miny},{bbox.maxx},{bbox.maxy}",
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"
