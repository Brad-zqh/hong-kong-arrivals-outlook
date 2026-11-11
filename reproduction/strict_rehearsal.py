"""Five-round rehearsal using archived vintages, then separately scored truth."""

import argparse
from collections import defaultdict
import csv
from datetime import date, datetime, timedelta
import json
from math import isfinite
from pathlib import Path
from statistics import mean, stdev

import backtest
from strict_rehearsal_sources import HISTORICAL_ORIGINS, HISTORICAL_PRETRAINING_DAY, noon, sha256


HORIZON = 15
MODELS = ("weekday_mean4", "chronos_joint_calendar")
CHRONOS_SHA = "ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42"


def days(first, end):
    return [first + timedelta(days=i) for i in range((end - first).days + 1)]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_release(archive_dir, meta, release_day):
    if datetime.fromisoformat(meta["release_noon_hkt"]) != noon(release_day):
        raise ValueError("Release date or cutoff does not match the rehearsal schedule")
    archived = datetime.fromisoformat(meta["archive_at_hkt"])
    if archived.date() != release_day or archived > noon(release_day):
        raise ValueError("Snapshot was not available at the simulated release")
    path = archive_dir / meta["file"]
    if sha256(path) != meta["sha256"]:
        raise ValueError("Archive content changed after download")
    arrivals, source = backtest.read_arrivals(path)
    last = release_day - timedelta(days=1)
    if source["last_date"] != last.isoformat() or meta["history_end"] != last.isoformat():
        raise ValueError("Snapshot must end the day before its release")
    return arrivals, last


def choose_ports(arrivals, last):
    history = days(backtest.TRAIN_START, last)
    totals = {}
    for port in sorted({key[0] for key in arrivals} - backtest.STRUCTURAL_BREAK_POINTS):
        keys = [(port, group) for group in backtest.GROUPS]
        if all(all(day in arrivals[key] for day in history) for key in keys):
            totals[port] = sum(arrivals[key][day] for key in keys for day in history)
    if len(totals) < 10:
        raise ValueError("Fewer than ten complete proxy ports in the pretraining release")
    return sorted(totals, key=lambda port: (-totals[port], port))[:10]


def forecast_release(arrivals, history_end, origin, keys, chronos, calendar_data, context):
    import numpy as np

    cutoff = history_end + timedelta(days=1)
    forecast_end = origin + timedelta(days=HORIZON - 1)
    history_days = days(max(backtest.TRAIN_START, cutoff - timedelta(days=context)), history_end)
    model_days = days(cutoff, forecast_end)
    # Snapshots are the sole target input. Earlier releases forecast across
    # their 1–2 day gap to reach the same official-shaped submission horizon.
    observed = np.array([[arrivals[key][day] for day in history_days] for key in keys], dtype="float32")
    future = calendar_data(model_days)
    projections = chronos(observed, calendar_data(history_days), future, horizon=len(model_days))[MODELS[1]]
    if any(part.shape != (len(model_days), len(keys)) for part in projections):
        raise ValueError("Unexpected forecast shape")
    projected = []
    offset = (origin - cutoff).days
    for index, key in enumerate(keys):
        values = arrivals[key]
        scale = backtest.scale(values, cutoff)
        residuals = backtest.calibration_errors(values, cutoff, MODELS[0])
        qlo, qhi = (backtest.quantile(residuals, p) for p in (0.15, 0.85))
        for lead, day in enumerate(days(origin, forecast_end), 1):
            point = backtest.predict(values, cutoff, day, MODELS[0])
            baseline = point, point + qlo, point + qhi
            model = tuple(float(array[offset + lead - 1, index]) for array in projections)
            for name, prediction in zip(MODELS, (baseline, model)):
                if not all(isfinite(x) for x in prediction) or prediction[1] > prediction[2]:
                    raise ValueError("Non-finite forecast or crossing interval")
                point, lower, upper = (max(0.0, x) for x in prediction)
                projected.append({
                    "day_hkt": day.isoformat(), "lead": lead, "control_point": key[0],
                    "visitor_group": key[1], "model": name, "point": point,
                    "lower70": lower, "upper70": upper, "scale": scale,
                })
    return projected


def forecast(args):
    import importlib.metadata
    import torch
    from chronos_calendar import CHRONOS_REVISION, CONTEXT, calendar_data, chronos_forecaster

    archive_manifest = args.archive_dir / "archive_manifest.json"
    archive = json.loads(archive_manifest.read_text(encoding="utf-8"))
    releases = archive["releases"]
    if [(r["round"], r["release"]) for r in releases] != [(i, j) for i in range(1, 6) for j in range(1, 4)]:
        raise ValueError("Expected five rounds with exactly three vintage releases each")
    pretraining = archive["pretraining_release"]
    initial, initial_end = load_release(args.archive_dir, pretraining, HISTORICAL_PRETRAINING_DAY)
    keys = [(port, group) for port in choose_ports(initial, initial_end) for group in backtest.GROUPS]
    weights_sha = sha256(args.weights / "model.safetensors")
    if weights_sha != CHRONOS_SHA:
        raise ValueError("Model checkpoint SHA-256 does not match the pinned official revision")
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.manual_seed(173)
    chronos = chronos_forecaster(args.weights, device=args.device, names={MODELS[1]})
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    for r in releases:
        origin = HISTORICAL_ORIGINS[r["round"] - 1]
        release_day = origin - timedelta(days=3 - r["release"])
        arrivals, last = load_release(args.archive_dir, r, release_day)
        rows = forecast_release(arrivals, last, origin, keys, chronos, calendar_data, CONTEXT)
        assert len(rows) == 600
        records.extend({"round": r["round"], "release": r["release"], "archive_version": r["archive_version"],
                        "history_end": last.isoformat(), **row} for row in rows)
        print(f"Round {r['round']} release {r['release']} complete ({r['archive_version']})", flush=True)
    path = args.out / "forecast_frozen.csv"
    write_csv(path, records)
    manifest = {
        "archive_manifest_sha256": sha256(archive_manifest), "pretraining_release": pretraining,
        "releases": releases,
        "series": keys, "models": list(MODELS), "chronos_revision": CHRONOS_REVISION,
        "chronos_weights_sha256": weights_sha, "chronos_context": CONTEXT,
        "model_released_before_first_rehearsal": True,
        "torch_version": torch.__version__, "chronos_version": importlib.metadata.version("chronos-forecasting"),
        "device": args.device, "forecast_rows": len(records), "forecast_sha256": sha256(path),
        "truth_loaded": False, "external_variables": ["weekday", "published_holiday_calendar"],
    }
    write_json(args.out / "forecast_manifest.json", manifest)
    print(f"Froze {len(records)} forecasts before reading realized values.", flush=True)


def write_workbooks(root, forecast_rows):
    from openpyxl import Workbook

    for round_number in range(1, 6):
        rows = [r for r in forecast_rows if int(r["round"]) == round_number and r["release"] == "3"
                and r["model"] == MODELS[1]]
        if len(rows) != 300:
            raise ValueError("Expected 300 submission rows for each track")
        for track, columns in (("point", ("point",)), ("interval70", ("lower70", "upper70"))):
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Rehearsal"
            sheet.append(["Date (HKT)", "Control Point", "Visitor Group", *columns])
            for r in rows:
                sheet.append([r["day_hkt"], r["control_point"], r["visitor_group"], *(float(r[c]) for c in columns)])
            sheet.freeze_panes = "D2"
            for column, width in zip("ABCDE", (17, 34, 21, 19, 19)):
                sheet.column_dimensions[column].width = width
            workbook.save(root / f"rehearsal-round-{round_number}-{track}.xlsx")


def score(args):
    path = args.out / "forecast_frozen.csv"
    manifest = json.loads((args.out / "forecast_manifest.json").read_text(encoding="utf-8"))
    if manifest["truth_loaded"] or sha256(path) != manifest["forecast_sha256"]:
        raise ValueError("Frozen forecast provenance mismatch")
    rows = read_csv(path)
    expected = {
        (r, stage, name, day.isoformat(), port, group)
        for r, origin in enumerate(HISTORICAL_ORIGINS, 1)
        for stage in range(1, 4) for name in MODELS
        for day in days(origin, origin + timedelta(days=14)) for port, group in manifest["series"]
    }
    actual_keys = {(int(r["round"]), int(r["release"]), r["model"], r["day_hkt"], r["control_point"],
                    r["visitor_group"]) for r in rows}
    if len(rows) != len(actual_keys) or actual_keys != expected:
        raise ValueError("Incomplete or duplicated predictions")
    actual, truth_info = backtest.read_arrivals(args.truth)
    cohorts = defaultdict(list)
    for r in rows:
        lead = int(r["lead"])
        origin = HISTORICAL_ORIGINS[int(r["round"]) - 1]
        day = date.fromisoformat(r["day_hkt"])
        assert day == origin + timedelta(days=lead - 1)
        if lead == 1:
            continue
        y = actual[(r["control_point"], r["visitor_group"])][day]
        point, lower, upper, scale = (float(r[k]) for k in ("point", "lower70", "upper70", "scale"))
        assert min(point, lower, upper) >= 0 and scale > 0 and lower <= upper
        winkler = (upper - lower + 2 / 0.3 * (max(0.0, lower - y) + max(0.0, y - upper))) / scale
        cohorts[(int(r["round"]), int(r["release"]), r["model"])].append(
            (abs(y - point) / scale, winkler, lower <= y <= upper)
        )
    scores = []
    for (number, release, model), values in sorted(cohorts.items()):
        if len(values) != 280:
            raise ValueError("Expected 280 scored values per draft or final release")
        mase, winkler, coverage = (mean(col) for col in zip(*values))
        scores.append({"round": number, "release": release, "model": model, "scored": len(values),
                       "mase": mase, "winkler": winkler, "coverage": coverage})
    write_csv(args.out / "release_scores.csv", scores)
    final = [r for r in scores if r["release"] == 3]
    write_csv(args.out / "final_round_scores.csv", final)
    summary = {}
    for model in MODELS:
        used = [row for row in final if row["model"] == model]
        by_metric = {}
        for metric in ("mase", "winkler"):
            best = sorted(used, key=lambda row: row[metric])[:4]
            by_metric[metric] = {
                "five_round_mean": mean(row[metric] for row in used),
                "five_round_sd": stdev(row[metric] for row in used),
                "best_four_mean": mean(row[metric] for row in best),
                "best_four_rounds": [row["round"] for row in best],
            }
        by_metric["coverage_five_rounds"] = mean(row["coverage"] for row in used)
        summary[model] = by_metric
    write_json(args.out / "score_summary.json", {
        "forecast_sha256": manifest["forecast_sha256"], "truth_file": args.truth.name,
        "truth_sha256": sha256(args.truth), "truth_source_info": truth_info, "models": summary,
        "submission_rows_per_model": 1500, "scored_final_rows_per_model": 1400,
        "metric_scale": "mean absolute 7-day seasonal difference from 2025-01-01 through the release history cutoff",
    })
    write_workbooks(args.out, rows)
    print(json.dumps(summary, indent=2))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    run = commands.add_parser("forecast")
    run.add_argument("--archive-dir", required=True, type=Path)
    run.add_argument("--out", required=True, type=Path)
    run.add_argument("--weights", required=True, type=Path)
    run.add_argument("--device", default="cpu", choices=("cpu", "cuda"))
    run.set_defaults(action=forecast)
    run = commands.add_parser("score")
    run.add_argument("--out", required=True, type=Path)
    run.add_argument("--truth", required=True, type=Path)
    run.set_defaults(action=score)
    args = cli.parse_args()
    args.action(args)


if __name__ == "__main__":
    main()
