# Hong Kong arrival checkpoints

`checkpoints.csv` contains the ten control points used by the public historical rehearsals. The English names in the CSV are the keys in the website's rehearsal data. Coordinates are longitude and latitude in EPSG:4326, drawn from the project's archived [Immigration Department CSDI Control Points dataset](https://portal.csdi.gov.hk/csdi-webpage/dataset/immd_rcd_1633320081376_19895). The airport uses the Terminal 1 reference point. The bridge uses the Hong Kong Port control point. Crossing modes follow the department's [report on air, land and sea traffic](https://www.immd.gov.hk/publications/a_report_2024/en/chapter3.html), with land crossings distinguished as rail or road. All points have equal visual weight within each panel.

The three panels share WGS 84 / UTM zone 50N (EPSG:32650). Dashed boxes show the exact extents of the detailed panels. The main map's graticule uses WGS 84 longitude and latitude. Scale bars use projected metres and the arrows show true north. The urban basemap uses roads, railways and land cover from [OpenStreetMap](https://www.openstreetmap.org/copyright) and water from the [Copernicus GLO-30 water body mask](https://registry.opendata.aws/copernicus-dem/). Point shape as well as color identifies crossing mode. The web map uses the same projected coordinates in two views.

## Reproduce

Download the two water masks into one directory and use the [Geofabrik Guangdong extract](https://download.geofabrik.de/asia/china/guangdong.html) for the city layers. The hashes identify the copies retrieved on 2026-11-14. The extract's OSM replication timestamp was 2026-11-13 21:22:20 UTC.

| Input | SHA-256 |
| --- | --- |
| [E113 water mask](https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N22_00_E113_00_DEM/AUXFILES/Copernicus_DSM_COG_10_N22_00_E113_00_WBM.tif) | `b9accb26c66298f48fe86b18198251b449e14c5fb6b51f9da66ac44661770d3d` |
| [E114 water mask](https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N22_00_E114_00_DEM/AUXFILES/Copernicus_DSM_COG_10_N22_00_E114_00_WBM.tif) | `4493d14116baa3c123a4056a04b89cf2f088fcf0e93bf0b522a0ddf48353f212` |
| [Guangdong OSM extract](https://download.geofabrik.de/asia/china/guangdong.html) | `5e2d10daafd752c55928324654f88baf7c980629cef88975586d67712835db40` |

With Python 3.12 and osmium, Shapely, NumPy, Matplotlib, Pillow, pyproj and Rasterio installed, run from the dashboard repository root. Supply your local Times New Roman font path:

```powershell
python -B reproduction/maps/extract_city.py local/gis/guangdong.osm.pbf local/gis/city.geojson
python -B reproduction/maps/render.py --tiles local/gis/tiles --osm local/gis/city.geojson --out local/gis/figures --font C:/Windows/Fonts/times.ttf
```

The script outputs a 300 dpi PNG and PDF with selectable text, a WebP map, and the backdrops and marker data used in the interactive view. Current street data provide geographic context for all historical rounds.
