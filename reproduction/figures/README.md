# MM-PortFlow architecture figure

Run from the dashboard repository root with Python, Matplotlib, NumPy, Pillow and OpenCV installed.

```powershell
python -B reproduction/figures/mm_portflow.py --out local/figure-vector --site
```

Use the SVG in `local/figure-vector` to edit text and paths. The PDF preserves selectable type. The PNG is a 2880 × 1929 reference for visual comparison. `--site` refreshes the public SVG with glyph outlines and the WebP fallback. The two exports use the same geometry. The platform marks, station photo and video frames are the figure's raster inputs. The text, curves and matrices illustrate the workflow. Media credits are under [Data sources and travel evidence](https://brad-zqh.github.io/hong-kong-arrivals-outlook/#evidence).

The lower panels follow the evidence attention and directed routing implementations. History conditions the queries, and evidence cells supply keys and values. The forecast multiplies the estimated group total by redistributed checkpoint shares. History supplies the interval widths.
