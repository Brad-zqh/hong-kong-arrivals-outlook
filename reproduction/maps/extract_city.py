"""Extract the streets, railways and land cover shown in the checkpoint map."""

import argparse
from collections import Counter
import json
from pathlib import Path

import osmium
from shapely import make_valid
from shapely.geometry import LineString, box, mapping, shape


BOUNDS = box(113.43, 22.07, 114.56, 22.76)
HIGHWAYS = {"motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified", "living_street"}
RAILWAYS = {"rail", "light_rail", "subway"}
FACTORY = osmium.geom.GeoJSONFactory()


def road_layer(tag: str) -> str:
    """Group road types by their visual role at regional and urban scales."""
    if tag in {"motorway", "trunk"}:
        return "highway"
    if tag in {"primary", "secondary", "tertiary"}:
        return tag
    return "street"


def extract(source: Path, output: Path) -> None:
    """Clip mapped features from a local OSM extract and save WGS84 GeoJSON."""
    reader = osmium.FileProcessor(source).with_locations().with_areas(
        osmium.filter.KeyFilter("leisure", "landuse", "natural")
    )
    features = []
    counts = Counter()
    invalid_areas = 0
    for item in reader:
        tags = item.tags
        geometry = None
        if item.is_way():
            road = tags.get("highway", "").removesuffix("_link")
            rail = tags.get("railway", "")
            if road in HIGHWAYS:
                layer = road_layer(road)
            elif rail in RAILWAYS and tags.get("tunnel") != "yes":
                layer = "rail"
            else:
                continue
            locations = [node.location for node in item.nodes]
            if len(locations) < 2 or not all(location.valid() for location in locations):
                continue
            geometry = LineString([(loc.lon, loc.lat) for loc in locations])
        elif item.is_area():
            if (tags.get("leisure") in {"park", "nature_reserve"} or
                    tags.get("landuse") in {"forest", "village_green"} or
                    tags.get("natural") in {"wood", "grassland"}):
                layer = "green"
            elif tags.get("landuse") in {"residential", "industrial", "commercial", "retail"}:
                layer = "built"
            else:
                continue
            try:
                geometry = shape(json.loads(FACTORY.create_multipolygon(item)))
            except osmium.InvalidLocationError:
                invalid_areas += 1
                continue
            except RuntimeError as error:
                if not str(error).startswith("invalid area"):
                    raise
                invalid_areas += 1
                continue
        if geometry is None or not geometry.intersects(BOUNDS):
            continue
        clipped = make_valid(geometry).intersection(BOUNDS)
        if clipped.is_empty:
            continue
        features.append({"type": "Feature", "properties": {"layer": layer}, "geometry": mapping(clipped)})
        counts[layer] += 1
    if not {"highway", "rail", "street", "green", "built"}.issubset(counts):
        raise ValueError(f"Missing layers in the extract: {counts}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
                      encoding="utf-8")
    print(f"Features kept: {dict(sorted(counts.items()))}; invalid areas skipped: {invalid_areas}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    extract(args.source, args.output)
