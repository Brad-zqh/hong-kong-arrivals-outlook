"""Recompute the five historical rounds and export the public rehearsal dashboard."""

import csv
from datetime import date, timedelta
import json
from math import isfinite
from pathlib import Path
from statistics import mean
import sys

ROOT = Path(__file__).resolve().parent
PRACTICE = ROOT.parent / "practice"
sys.path.insert(0, str(PRACTICE))
import backtest

SCHEDULE = ["2026-12-14", "2027-01-12", "2027-02-17", "2027-03-18", "2027-04-16"]
MODELS = {
    "chronos_joint_calendar": "Chronos-2 + 日历",
    "chronos_joint": "Chronos-2 多序列",
    "chronos_independent": "Chronos-2 单序列",
    "weekday_mean4": "四周同星期均值",
}


def build_rehearsal():
    folder = PRACTICE / "seasonal_rehearsal"
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    with (folder / "predictions.csv").open(encoding="utf-8", newline="") as handle:
        saved = list(csv.DictReader(handle))
    arrivals, coverage = backtest.read_arrivals()
    series = [tuple(key) for key in summary["series"]]
    assert len(series) == len(set(series)) == 20
    rounds = []
    for index, (prior, official) in enumerate(zip(summary["origins"], SCHEDULE, strict=True), 1):
        origin = date.fromisoformat(prior)
        dates = [(origin + timedelta(days=offset)).isoformat() for offset in range(15)]
        expected = {(day, port, group) for day in dates for port, group in series}
        rows = [row for row in saved if row["origin"] == prior]
        assert len(rows) == 300 and {(r["date"], r["port"], r["group"]) for r in rows} == expected
        releases = []
        baseline = {}
        for days_before in (2, 1, 0):
            cutoff = origin - timedelta(days=days_before)
            errors = []
            for key in series:
                # Each mock release sees targets only through the preceding date.
                history = {day: n for day, n in arrivals[key].items() if day < cutoff}
                scale = backtest.scale(history, cutoff)
                for offset in range(15):
                    day = origin + timedelta(days=offset)
                    prediction = backtest.predict(history, cutoff, day, "weekday_mean4")
                    if offset:
                        errors.append(abs(arrivals[key][day] - prediction) / scale)
                    if days_before == 0:
                        baseline[(day.isoformat(), *key)] = prediction
            releases.append({
                "release": cutoff.isoformat(), "historyThrough": (cutoff - timedelta(days=1)).isoformat(),
                "mase": mean(errors),
            })
        data = []
        scores = {}
        for row in rows:
            key = row["date"], row["port"], row["group"]
            actual = int(row["actual"])
            assert actual == arrivals[key[1:]][date.fromisoformat(key[0])]
            assert abs(baseline[key] - float(row["weekday_mean4_point"])) < 1e-6
            values = {}
            for model in MODELS:
                point, lo, hi = (float(row[f"{model}_{field}"]) for field in ("point", "lower", "upper"))
                assert all(isfinite(value) for value in (point, lo, hi)) and 0 <= lo <= hi and point >= 0
                values[model] = [round(value, 3) for value in (point, lo, hi)]
            data.append([row["date"], series.index(key[1:]), actual, values])
        scored = [row for row in rows if int(row["lead"]) > 1]
        for model in MODELS:
            scores[model] = {
                "mase": mean(float(row[f"{model}_mase"]) for row in scored),
                "winkler": mean(float(row[f"{model}_winkler"]) for row in scored),
                "coverage": mean(row[f"{model}_coverage"] == "True" for row in scored),
            }
        assert abs(scores["weekday_mean4"]["mase"] - releases[-1]["mase"]) < 1e-6
        submission = date.fromisoformat(official)
        rounds.append({
            "number": index, "origin": prior, "end": dates[-1], "official": official,
            "officialEnd": (submission + timedelta(days=14)).isoformat(),
            "officialReleases": [(submission - timedelta(days=delta)).isoformat() for delta in (2, 1, 0)],
            "data": data, "scores": scores, "baselineReleases": releases,
        })
    return {
        "models": MODELS, "series": series, "rounds": rounds, "source": coverage,
        "chronosRevision": summary["chronos_revision"], "sourceUrl": backtest.SOURCE_URL,
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
    result = build_rehearsal()
    site = ROOT / "site"
    (site / "rehearsal.js").write_text(
        "window.REHEARSAL = " + json.dumps(result, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    save_mock_workbooks(result, site / "exports")
    print("5 rounds, 15 mock releases, 1,500 predictions and 1,400 scored rows per model.")
