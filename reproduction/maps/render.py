"""Render the rehearsal checkpoints over a city basemap."""

import argparse
import csv
from dataclasses import dataclass
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patheffects
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.lines import Line2D
from matplotlib.patches import PathPatch, Polygon, Rectangle
from matplotlib.path import Path as PlotPath
import numpy as np
from PIL import Image
from pyproj import Transformer
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject
from shapely.geometry import box, shape
from shapely.geometry.polygon import orient
from shapely.ops import transform as project_geometry


CRS = "EPSG:32650"
PROJECT = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
INK = "#17304a"
MUTED = "#516879"
GRID = "#8198a6"
WATER = "#c1dfed"
LAND = "#f5f1e7"
FOCUS = "#986149"
MODES = {
    "Air": ("D", "#14736c"),
    "Road": ("s", "#b25e1e"),
    "Rail": ("o", "#24558d"),
    "Sea": ("^", "#78476f"),
}
ATTRIBUTION = (
    "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 "
    "provided under COPERNICUS by the European Union and ESA; all rights reserved."
)
REGIONAL = (113.990, 22.410, 110_000)
HONG_KONG = (114.080, 22.387, 56_000)
HARBOUR = (114.165, 22.290, 12_000)
STYLES = {
    "built": ("#ebe0ce", 0),
    "green": ("#c5d8ba", 0),
    "street": ("#c3b7a5", 0.25),
    "tertiary": ("#b6a28a", 0.35),
    "secondary": ("#cc996d", 0.55),
    "primary": ("#c47b49", 0.65),
    "highway": ("#b36936", 0.80),
    "rail": ("#748398", 0.55),
}


@dataclass(frozen=True)
class Checkpoint:
    number: int
    name: str
    mode: str
    x: float
    y: float


def checkpoints(path: Path) -> list[Checkpoint]:
    """Read the model's rehearsal checkpoint coordinates in WGS84."""
    with path.open(encoding="utf-8", newline="") as handle:
        points = [
            Checkpoint(
                int(row["id"]), row["checkpoint"], row["mode"],
                *PROJECT.transform(float(row["longitude"]), float(row["latitude"])),
            )
            for row in csv.DictReader(handle)
        ]
    if {point.number for point in points} != set(range(1, 11)) or len(points) != 10:
        raise ValueError("Expected 10 uniquely numbered rehearsal checkpoints.")
    if len({(point.x, point.y) for point in points}) != 10:
        raise ValueError("Checkpoint coordinates must be distinct.")
    return points


def viewport(ax: plt.Axes, center: tuple[float, float, int]) -> None:
    """Set axis limits in metres with equal horizontal and vertical scales."""
    centre_x, centre_y = PROJECT.transform(*center[:2])
    width = center[2]
    position = ax.get_position()
    height = width * position.height * ax.figure.get_figheight() / (position.width * ax.figure.get_figwidth())
    ax.set_xlim(centre_x - width / 2, centre_x + width / 2)
    ax.set_ylim(centre_y - height / 2, centre_y + height / 2)
    ax.set_aspect("equal")


def water_mask(ax: plt.Axes, tiles: Path, resolution: int) -> np.ndarray:
    """Reproject the two Copernicus water masks to the matching panel grid."""
    west, east = ax.get_xlim()
    south, north = ax.get_ylim()
    cols = int(np.ceil((east - west) / resolution))
    rows = int(np.ceil((north - south) / resolution))
    dx, dy = (east - west) / cols, (north - south) / rows
    transform = from_origin(west, north, dx, dy)
    mosaic = np.full((rows, cols), 255, dtype=np.uint8)
    for tile in ("113", "114"):
        path = tiles / f"Copernicus_DSM_COG_10_N22_00_E{tile}_00_WBM.tif"
        with rasterio.open(path) as source:
            if source.crs.to_epsg() != 4326:
                raise ValueError(f"Expected WGS84 coordinates: {path}")
            reproject(rasterio.band(source, 1), mosaic, dst_transform=transform, dst_crs=CRS,
                      dst_nodata=255, resampling=Resampling.nearest, init_dest_nodata=False)
    if not np.isin(mosaic, [0, 1, 2, 3]).all():
        raise ValueError("The source tiles do not cover the map extent.")
    return mosaic


def geometry_parts(geometry):
    """Yield drawable single geometries, retaining polygon holes."""
    if hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from geometry_parts(part)
    elif not geometry.is_empty:
        yield geometry


def basemap(ax: plt.Axes, tiles: Path, city: dict, resolution: int, layers: tuple[str, ...]) -> None:
    """Draw land, water, parks and roads in a restrained city palette."""
    west, east = ax.get_xlim()
    south, north = ax.get_ylim()
    clip = box(west, south, east, north)
    water = water_mask(ax, tiles, resolution)
    colours = np.empty((*water.shape, 3), dtype=np.float32)
    colours[:] = matplotlib.colors.to_rgb(LAND)
    colours[water != 0] = matplotlib.colors.to_rgb(WATER)
    ax.imshow(colours, extent=(west, east, south, north),
              interpolation="bilinear", zorder=0)
    for layer in layers:
        colour, width = STYLES[layer]
        geometry = [part for feature in city[layer] if feature.intersects(clip)
                    for part in geometry_parts(feature.intersection(clip))]
        if width == 0:
            patches = []
            for polygon in geometry:
                if polygon.geom_type != "Polygon":
                    continue
                polygon = orient(polygon, sign=1)
                rings = [PlotPath(np.array(ring.coords), closed=True)
                         for ring in (polygon.exterior, *polygon.interiors)]
                patches.append(PathPatch(PlotPath.make_compound_path(*rings)))
            ax.add_collection(PatchCollection(patches, facecolor=colour, edgecolor="none",
                                              zorder=0.2, rasterized=True))
        else:
            segments = [np.asarray(line.coords) for line in geometry if line.geom_type == "LineString"]
            ax.add_collection(LineCollection(segments, colors=colour, linewidths=width,
                                             capstyle="round", zorder=0.6, rasterized=True))
    ax.set(xticks=[], yticks=[])
    for spine in ax.spines.values():
        spine.set(color="#718a9d", linewidth=0.65)


def graticule(ax: plt.Axes, longitudes: list[float], latitudes: list[float]) -> None:
    """Plot WGS84 parallels and meridians in the display projection."""
    west, east = ax.get_xlim()
    south, north = ax.get_ylim()
    options = dict(color=GRID, lw=0.48, alpha=0.65, dashes=(2, 3), zorder=1)
    for lon in longitudes:
        lat = np.linspace(22.0, 23.0, 61)
        x, y = PROJECT.transform(np.full_like(lat, lon), lat)
        ax.plot(x, y, **options)
        edge = np.interp(south, y, x)
        if west < edge < east:
            ax.annotate(f"{lon:g}°E", (edge, south), xytext=(0, -3.5), textcoords="offset points",
                        ha="center", va="top", color=MUTED, fontsize=7.5)
    for lat in latitudes:
        lon = np.linspace(113.0, 115.0, 61)
        x, y = PROJECT.transform(lon, np.full_like(lon, lat))
        ax.plot(x, y, **options)
        edge = np.interp(west, x, y)
        if south < edge < north:
            ax.annotate(f"{lat:g}°N", (west, edge), xytext=(-4, 0), textcoords="offset points",
                        ha="right", va="center", color=MUTED, fontsize=7.5)


def scale(ax: plt.Axes, km: int) -> None:
    """Add a scale bar defined in projected metres."""
    west, east = ax.get_xlim()
    south, north = ax.get_ylim()
    x = west + (east - west) * 0.05
    y = south + (north - south) * 0.08
    height = (north - south) * 0.012
    plate = Rectangle((x - (east - west) * 0.023, y - (north - south) * 0.05),
                      km * 1000 + (east - west) * 0.065, (north - south) * 0.085,
                      facecolor="white", edgecolor="none", alpha=0.87, zorder=7)
    ax.add_patch(plate)
    for index, fill in enumerate((INK, "white")):
        ax.add_patch(Rectangle((x + index * km * 500, y), km * 500, height,
                               facecolor=fill, edgecolor=INK, linewidth=0.55, zorder=7))
    for offset, label in ((0, "0"), (km / 2, f"{km / 2:g}"), (km, f"{km} km")):
        ax.annotate(label, (x + 1000 * offset, y), xytext=(0, -2), textcoords="offset points",
                    ha="center", va="top", fontsize=8, color=INK, zorder=7)


def focus_bounds(ax: plt.Axes, child: plt.Axes, label: str) -> None:
    """Show the exact extent of a detail panel in its parent map."""
    west, east = child.get_xlim()
    south, north = child.get_ylim()
    ax.add_patch(Rectangle((west, south), east - west, north - south, fill=False,
                           edgecolor=FOCUS, lw=1.25, linestyle=(0, (4, 2)), zorder=3))
    ax.annotate(label, (east, south), xytext=(-3, -4), textcoords="offset points",
                va="top", ha="right", weight="bold", color=FOCUS, fontsize=10,
                path_effects=[patheffects.withStroke(linewidth=2.8, foreground="white")])


def place(ax: plt.Axes, name: str, lon: float, lat: float, water: bool = False) -> None:
    """Label a geographic feature at a manually chosen display anchor."""
    ax.text(*PROJECT.transform(lon, lat), name, ha="center", va="center", color=MUTED,
            fontsize=9, fontstyle="italic" if water else "normal", zorder=2,
            path_effects=[patheffects.withStroke(linewidth=2.4, foreground=WATER if water else "#f8f5ea")])


def draw_points(ax: plt.Axes, points: list[Checkpoint], labels: dict[int, tuple[str, float, float]]) -> None:
    """Plot official coordinates and connect them to offset labels."""
    for point in points:
        marker, colour = MODES[point.mode]
        ax.scatter(point.x, point.y, marker=marker, color=colour, edgecolor="white",
                   s=55 if point.number in labels else 31, linewidth=0.9, zorder=5)
        if point.number not in labels:
            continue
        text, lon, lat = labels[point.number]
        ax.annotate(f"{point.number}  {text}", (point.x, point.y),
                    xytext=PROJECT.transform(lon, lat), ha="left", va="center",
                    fontsize=10, weight="bold", color=INK, linespacing=1.0,
                    bbox=dict(facecolor="white", edgecolor="none", pad=1.6, alpha=0.90),
                    arrowprops=dict(arrowstyle="-", color=colour, shrinkA=1, shrinkB=3.2, lw=0.88),
                    zorder=6)


def compass(ax: plt.Axes, lon: float, lat: float) -> None:
    """Draw a true-north arrow, rotated for local UTM grid convergence."""
    xy = np.array(PROJECT.transform(lon, lat))
    north = np.array(PROJECT.transform(lon, lat + 0.01)) - xy
    north /= np.linalg.norm(north)
    right = np.array((north[1], -north[0]))
    span = (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.073
    tip = xy + span * north
    for side, colour in ((-1, "white"), (1, INK)):
        ax.add_patch(Polygon([tip, xy + side * span * 0.24 * right, xy + span * 0.25 * north],
                             closed=True, facecolor=colour, edgecolor=INK, linewidth=0.72, zorder=9))
    ax.annotate("N", tip, xytext=(0, 2), textcoords="offset points",
                ha="center", va="bottom", weight="bold", color=INK, fontsize=9, zorder=9)


def interactive_maps(tiles: Path, city: dict, points: list[Checkpoint], output: Path) -> None:
    """Render map backdrops and normalized point coordinates for the website."""
    with Path(__file__).with_name("checkpoints.csv").open(encoding="utf-8", newline="") as handle:
        names = {int(row["id"]): row["zh"] for row in csv.DictReader(handle)}
    locations = {}
    for name, center, shown, resolution, layers, size in (
        ("overview", HONG_KONG, points[:7], 35, ("built", "green", "secondary", "primary", "highway", "rail"), (8, 6)),
        ("harbour", HARBOUR, points[7:], 14, tuple(STYLES), (8, 5.2)),
    ):
        figure = plt.figure(figsize=size)
        ax = figure.add_axes((0, 0, 1, 1))
        viewport(ax, center)
        basemap(ax, tiles, city, resolution, layers)
        if name == "overview":
            place(ax, "Shenzhen", 114.022, 22.585)
            place(ax, "Lantau Island", 113.962, 22.252)
            place(ax, "Hong Kong Island", 114.175, 22.240)
            compass(ax, 114.321, 22.522)
        else:
            place(ax, "Kowloon", 114.175, 22.320)
            place(ax, "Victoria Harbour", 114.197, 22.280, True)
            compass(ax, 114.212, 22.314)
        scale(ax, 10 if name == "overview" else 2)
        ax.text(0.992, 0.009, "© OpenStreetMap contributors", transform=ax.transAxes, ha="right",
                va="bottom", fontsize=7, color=MUTED, zorder=10,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, pad=1))
        figure.savefig(output / f"checkpoint-{name}.webp", dpi=180,
                       pil_kwargs={"quality": 93, "method": 6})
        plt.close(figure)
        west, east = ax.get_xlim()
        south, north = ax.get_ylim()
        locations[name] = [
            {"id": p.number, "en": p.name, "zh": names[p.number], "mode": p.mode,
             "x": round((p.x - west) / (east - west) * 100, 4),
             "y": round((north - p.y) / (north - south) * 100, 4)}
            for p in shown
        ]
        if name == "overview":
            x, y = PROJECT.transform(*HARBOUR[:2])
            locations["inset"] = [round((x - west) / (east - west) * 100, 4),
                                  round((north - y) / (north - south) * 100, 4)]
    (output / "checkpoint-locations.js").write_text(
        "window.CHECKPOINT_LOCATIONS = " + json.dumps(locations, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )


def render(tiles: Path, osm: Path, output: Path, font: Path) -> None:
    """Render a three-panel publication map and export vector text in the PDF."""
    fontManager.addfont(font)
    family = FontProperties(fname=font).get_name()
    plt.rcParams.update({"font.family": family, "mathtext.fontset": "stix", "pdf.fonttype": 42})
    output.mkdir(parents=True, exist_ok=True)
    points = checkpoints(Path(__file__).with_name("checkpoints.csv"))
    city = {layer: [] for layer in STYLES}
    for feature in json.loads(osm.read_text(encoding="utf-8"))["features"]:
        layer = feature["properties"]["layer"]
        geom = project_geometry(PROJECT.transform, shape(feature["geometry"]))
        city[layer].append(geom)
    figure = plt.figure(figsize=(12.2, 7.0), facecolor="white")
    regional = figure.add_axes((0.015, 0.529, 0.330, 0.457))
    harbour = figure.add_axes((0.015, 0.057, 0.330, 0.457))
    main = figure.add_axes((0.378, 0.057, 0.610, 0.929))

    for ax, extent, resolution, title, layers in (
        (regional, REGIONAL, 74, "(a) Pearl River Estuary", ("built", "green", "highway")),
        (main, HONG_KONG, 28, "(b) Hong Kong", ("built", "green", "secondary", "primary", "highway", "rail")),
        (harbour, HARBOUR, 18, "(c) Victoria Harbour", tuple(STYLES)),
    ):
        viewport(ax, extent)
        basemap(ax, tiles, city, resolution, layers)
        ax.text(0.026, 0.974, title, transform=ax.transAxes, ha="left", va="top",
                fontsize=13, weight="bold", color=INK, zorder=8,
                bbox=dict(facecolor="white", alpha=0.90, edgecolor="none", pad=3))

    graticule(main, [113.90, 114.00, 114.10, 114.20, 114.30], [22.20, 22.30, 22.40, 22.50, 22.60])
    focus_bounds(regional, main, "b")
    focus_bounds(main, harbour, "c")
    for name, lon, lat, water in (
        ("SHENZHEN", 114.025, 22.591, False), ("NEW TERRITORIES", 114.112, 22.443, False),
        ("LANTAU ISLAND", 113.956, 22.259, False), ("HONG KONG ISLAND", 114.169, 22.236, False),
        ("South China Sea", 114.270, 22.204, True),
    ):
        place(main, name, lon, lat, water)
    for name, lon, lat, water in (
        ("ZHUHAI", 113.545, 22.315, False), ("MACAO", 113.540, 22.162, False),
        ("SHENZHEN", 113.978, 22.635, False), ("HONG KONG", 114.135, 22.369, False),
        ("Pearl River", 113.696, 22.581, True),
    ):
        place(regional, name, lon, lat, water)
    for name, lon, lat, water in (
        ("KOWLOON", 114.180, 22.318, False), ("Victoria Harbour", 114.198, 22.284, True),
        ("HONG KONG ISLAND", 114.190, 22.264, False),
    ):
        place(harbour, name, lon, lat, water)

    draw_points(main, points, {
        1: ("Hong Kong\n    International Airport", 113.858, 22.347),
        2: ("Hong Kong–Zhuhai–Macao\n    Bridge Hong Kong Port", 113.848, 22.286),
        3: ("Shenzhen Bay", 113.855, 22.521),
        4: ("Lok Ma Chau Spur Line", 113.930, 22.470),
        5: ("Lo Wu", 114.087, 22.569),
        6: ("Man Kam To", 114.157, 22.495),
        7: ("Heung Yuen Wai", 114.193, 22.564),
    })
    draw_points(harbour, points[7:], {
        8: ("West Kowloon\n    High-Speed Rail", 114.110, 22.318),
        9: ("China Ferry\n    Terminal", 114.183, 22.306),
        10: ("Macau Ferry Terminal", 114.121, 22.272),
    })
    for ax, km in ((main, 10), (regional, 20), (harbour, 2)):
        scale(ax, km)

    compass(main, 114.320, 22.538)
    compass(regional, 114.475, 22.615)
    compass(harbour, 114.216, 22.316)

    handles = [
        Line2D([], [], marker=marker, markersize=6, markerfacecolor=colour,
               markeredgewidth=0, linestyle="none", label=mode)
        for mode, (marker, colour) in MODES.items()
    ]
    handles += [
        Line2D([], [], color=STYLES["highway"][0], lw=1.3, label="Major roads"),
        Line2D([], [], color=STYLES["rail"][0], lw=1, label="Railways"),
        Line2D([], [], color=STYLES["green"][0], lw=4, label="Green space"),
    ]
    main.legend(handles=handles, ncol=2, loc="center right", bbox_to_anchor=(0.974, 0.446),
                facecolor="white", framealpha=0.94, edgecolor="#d7e0e0",
                fontsize=8.7, labelcolor=INK, columnspacing=0.9, handlelength=1.6)
    main.text(0.991, 0.009, "© OpenStreetMap contributors", transform=main.transAxes,
              color=MUTED, ha="right", va="bottom", fontsize=6.5, zorder=8,
              url="https://www.openstreetmap.org/copyright",
              bbox=dict(facecolor="white", edgecolor="none", pad=1, alpha=0.82))

    stem = output / "hong-kong-checkpoints"
    figure.savefig(stem.with_suffix(".pdf"), dpi=300, metadata={
        "Title": "Hong Kong arrival checkpoints",
        "Subject": f"Control points: Hong Kong Immigration Department. City data: OpenStreetMap. {ATTRIBUTION}",
    })
    figure.savefig(stem.with_suffix(".png"), dpi=300)
    plt.close(figure)
    with Image.open(stem.with_suffix(".png")) as preview:
        preview.thumbnail((2440, 1400), Image.Resampling.LANCZOS)
        preview.convert("RGB").save(stem.with_suffix(".webp"), quality=94, method=6)
    interactive_maps(tiles, city, points, output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiles", type=Path, required=True)
    parser.add_argument("--osm", type=Path, required=True, help="City GeoJSON from extract_city.py")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True, help="Path to Times New Roman Regular")
    args = parser.parse_args()
    render(args.tiles, args.osm, args.out, args.font)


if __name__ == "__main__":
    main()
