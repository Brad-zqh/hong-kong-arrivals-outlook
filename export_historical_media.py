"""Export only numbered retrospective rounds for the public dashboard."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean


LABELS = {
    "fusion_temporal_history": ("客流＋日历", "Arrivals + calendar"),
    "fusion_temporal_early": ("向量 · 早期融合", "Embeddings · early"),
    "fusion_temporal_intermediate": ("向量 · 中期融合", "Embeddings · intermediate"),
    "fusion_temporal_late": ("向量 · 后期融合", "Embeddings · late"),
    "aligned_early": ("线索 · 早期融合", "Cues · early"),
    "aligned_intermediate": ("线索 · 中期融合", "Cues · intermediate"),
    "aligned_late": ("线索 · 后期融合", "Cues · late"),
    "aligned_text": ("线索 · 仅正文", "Cues · text only"),
    "aligned_half": ("线索 · 半量", "Cues · half sample"),
    "demand_text": ("加旅游文本线索", "+ travel cues from text"),
    "demand_multimodal": ("加照片、封面和视频帧", "+ photos, covers and frames"),
}
SEEDS = {"173", "271", "509"}
KEYS = ("point", "lower", "upper")


def export(run: Path, site: Path) -> None:
    prefix = "window.REHEARSAL = "
    report = json.loads((site / "rehearsal.js").read_text(encoding="utf-8").strip().removeprefix(prefix).removesuffix(";"))
    series = [tuple(pair) for pair in report["series"]]
    historical = {str(r["number"]): r for r in report["rounds"]}
    windows = {
        round_no: {(day, series_idx): actual for day, series_idx, actual, *_ in round_data["data"]}
        for round_no, round_data in historical.items()
    }
    forecasts, scores = defaultdict(dict), defaultdict(dict)
    with (run / "forecast_frozen.csv").open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            round_no = row["round"]
            if round_no not in historical:
                continue
            model, seed = row["model"].rsplit("-", 1)
            if model not in LABELS:
                continue
            series_idx = series.index((row["port"], row["group"]))
            key = (round_no, row["date"], series_idx, model)
            assert seed not in forecasts[key]
            forecasts[key][seed] = [float(row[field]) for field in KEYS]
    with (run / "round_scores.csv").open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            if row["round"] not in historical:
                continue
            model, seed = row["model"].rsplit("-", 1)
            if model in LABELS:
                scores[model][(row["round"], seed)] = [float(row[key]) for key in ("mase", "winkler", "coverage")]
    labels = {model: pair for model, pair in LABELS.items() if model in scores}
    assert labels and all(len(window) == 300 for window in windows.values())
    assert len(forecasts) == len(historical) * 300 * len(labels)
    data, csv_rows = {}, []
    for round_no, observed in windows.items():
        data[round_no] = []
        for (day, series_idx), actual in sorted(observed.items()):
            values = {}
            for model in labels:
                fits = forecasts[(round_no, day, series_idx, model)]
                assert fits.keys() == SEEDS
                point, low, high = [round(mean(column), 2) for column in zip(*fits.values())]
                assert 0 <= low <= point <= high
                values[model] = [point, low, high]
                csv_rows.append([round_no, day, *series[series_idx], model, actual, point, low, high])
            data[round_no].append([day, series_idx, actual, values])
    assert all(set(rows) == {(round_no, seed) for round_no in historical for seed in SEEDS}
               for rows in scores.values())
    payload = {
        "series": series,
        "labels": {key: pair[0] for key, pair in labels.items()},
        "labelsEn": {key: pair[1] for key, pair in labels.items()},
        "data": data,
        "metrics": {key: dict(zip(("mase", "winkler", "coverage"), map(mean, zip(*scores[key].values()))))
                    for key in labels},
    }
    (site / "multimodal.js").write_text("window.MULTIMODAL = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    with (site / "exports" / "multimodal-historical.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["round", "date_hkt", "proxy_checkpoint", "visitor_group", "model", "observed", "point_seed_mean", "q15_seed_mean", "q85_seed_mean"])
        writer.writerows(csv_rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    export(args.run, Path(__file__).parent / "site")
