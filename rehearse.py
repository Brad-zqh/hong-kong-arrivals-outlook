"""Export the archived five-round rehearsal for the public dashboard."""

import argparse
import csv
from datetime import date, timedelta
import json
from math import isfinite
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PRACTICE = ROOT.parent / "practice"
sys.path.insert(0, str(PRACTICE))
import backtest

MODELS = {
    "chronos_joint_calendar": "Chronos-2 + 日历",
    "weekday_mean4": "四周同星期均值",
}


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_rehearsal(folder, truth_path):
    from strict_rehearsal_sources import sha256

    forecast = json.loads((folder / "forecast_manifest.json").read_text(encoding="utf-8"))
    scored = json.loads((folder / "score_summary.json").read_text(encoding="utf-8"))
    raw = folder / "forecast_frozen.csv"
    assert sha256(raw) == forecast["forecast_sha256"] == scored["forecast_sha256"]
    assert sha256(truth_path) == scored["truth_sha256"]
    predictions = [row for row in read_rows(raw) if row["release"] == "3"]
    scores = {(int(r["round"]), int(r["release"]), r["model"]): {
        metric: float(r[metric]) for metric in ("mase", "winkler", "coverage")
    } for r in read_rows(folder / "release_scores.csv")}
    arrivals, coverage = backtest.read_arrivals(truth_path)
    series = [tuple(key) for key in forecast["series"]]
    assert len(series) == len(set(series)) == 20
    rounds = []
    for index in range(1, 6):
        snapshots = [r for r in forecast["releases"] if r["round"] == index]
        assert len(snapshots) == 3
        prior = snapshots[2]["origin"]
        origin = date.fromisoformat(prior)
        official = snapshots[2]["official_origin"]
        dates = [(origin + timedelta(days=offset)).isoformat() for offset in range(15)]
        expected = {(day, port, group) for day in dates for port, group in series}
        keyed = {}
        rows = [row for row in predictions if int(row["round"]) == index]
        for row in rows:
            key = row["day_hkt"], row["control_point"], row["visitor_group"]
            point, lo, hi = (float(row[field]) for field in ("point", "lower70", "upper70"))
            assert all(isfinite(value) for value in (point, lo, hi)) and 0 <= lo <= hi and point >= 0
            keyed.setdefault(key, {})[row["model"]] = [point, lo, hi]
        assert len(rows) == 300 * len(MODELS) and set(keyed) == expected
        assert all(set(values) == set(MODELS) for values in keyed.values())
        data = [[day, i, arrivals[key][date.fromisoformat(day)], keyed[(day, *key)]]
                for day in dates for i, key in enumerate(series)]
        releases = [{
            "release": r["release_noon_hkt"][:10], "historyThrough": r["history_end"],
            "archiveAt": r["archive_at_hkt"][11:16],
            "scores": {model: scores[(index, r["release"], model)] for model in MODELS},
        } for r in snapshots]
        submission = date.fromisoformat(official)
        rounds.append({
            "number": index, "origin": prior, "end": dates[-1], "official": official,
            "officialEnd": (submission + timedelta(days=14)).isoformat(),
            "officialReleases": [(submission - timedelta(days=delta)).isoformat() for delta in (2, 1, 0)],
            "data": data, "scores": releases[-1]["scores"], "releases": releases,
        })
    return {
        "models": MODELS, "series": series, "rounds": rounds, "source": coverage,
        "chronosRevision": forecast["chronos_revision"], "sourceUrl": backtest.SOURCE_URL,
    }


def save_mock_workbooks(report, out):
    from openpyxl import Workbook

    out.mkdir(exist_ok=True)
    for round_data in report["rounds"]:
        workbook = Workbook()
        info = workbook.active
        info.title = "Rehearsal"
        info.append(["Historical rehearsal", "Practice layout"])
        info.append(["Origin", round_data["origin"]])
        info.append(["Model", "Chronos-2 + calendar"])
        info.append(["Scored horizon", "Days 2–15"])
        point = workbook.create_sheet("Point")
        interval = workbook.create_sheet("Interval70")
        point.append(["Date", "Control Point", "Visitor Group", "Point Forecast"])
        interval.append(["Date", "Control Point", "Visitor Group", "Lower 15%", "Upper 85%"])
        for day, index, _, values in round_data["data"]:
            port, group = report["series"][index]
            forecast, lower, upper = values["chronos_joint_calendar"]
            point.append([day, port, group, forecast])
            interval.append([day, port, group, lower, upper])
        for sheet in (point, interval):
            sheet.freeze_panes = "D2"
            sheet.auto_filter.ref = sheet.dimensions
            for column, width in zip("ABCDE", (15, 33, 21, 19, 19)):
                sheet.column_dimensions[column].width = width
        workbook.save(out / f"rehearsal-round-{round_data['number']}.xlsx")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--results", type=Path, default=PRACTICE / "strict_rehearsal")
    cli.add_argument("--truth", type=Path, required=True)
    args = cli.parse_args()
    result = build_rehearsal(args.results, args.truth)
    site = ROOT / "site"
    (site / "rehearsal.js").write_text(
        "window.REHEARSAL = " + json.dumps(result, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    save_mock_workbooks(result, site / "exports")
    print("5 rounds, 15 mock releases, 1,500 predictions and 1,400 scored rows per model.")
