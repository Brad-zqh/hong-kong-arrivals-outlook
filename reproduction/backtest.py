"""Run a pre-competition proxy backtest on Hong Kong's public arrivals data."""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data" / "daily_passenger_traffic_2026-11-09.csv"
SOURCE_URL = "https://www.immd.gov.hk/opendata/eng/transport/immigration_clearance/statistics_on_daily_passenger_traffic.csv"
OUTPUT = ROOT / "results"
CUTOFFS = [date(2026, month, 1) for month in (2, 4, 6, 8, 10)]
GROUPS = ("Mainland Visitors", "Other Visitors")
METHODS = ("last_week", "weekday_mean4", "weekday_median8")
ALPHA = 0.30
TRAIN_START = date(2025, 1, 1)
STRUCTURAL_BREAK_POINTS = {"Lok Ma Chau", "Huanggang"}


def quantile(values: list[float], probability: float) -> float:
    """Return a linearly interpolated empirical quantile."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile requires at least one observation")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    fraction = position - lower
    if lower + 1 == len(ordered):
        return ordered[lower]
    return ordered[lower] * (1 - fraction) + ordered[lower + 1] * fraction


def read_arrivals(source: Path | None = None) -> tuple[dict[tuple[str, str], dict[date, int]], dict[str, object]]:
    """Load arrival visitor counts and check the source's row arithmetic."""
    series: dict[tuple[str, str], dict[date, int]] = defaultdict(dict)
    row_count = 0
    arrival_count = 0
    mismatches = 0
    with (source if source is not None else SOURCE).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"Date", "Control Point", "Arrival / Departure", "Hong Kong Residents", *GROUPS, "Total"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing expected columns: {required - set(reader.fieldnames or [])}")
        for row in reader:
            row_count += 1
            observed_date = datetime.strptime(row["Date"], "%d-%m-%Y").date()
            point = row["Control Point"].replace("Macao Ferry Terminal", "Macau Ferry Terminal")
            residents = int(row["Hong Kong Residents"].replace(",", ""))
            mainland = int(row["Mainland Visitors"].replace(",", ""))
            other = int(row["Other Visitors"].replace(",", ""))
            total = int(row["Total"].replace(",", ""))
            mismatches += residents + mainland + other != total
            if row["Arrival / Departure"] != "Arrival":
                continue
            arrival_count += 1
            for group, value in ((GROUPS[0], mainland), (GROUPS[1], other)):
                key = (point, group)
                if observed_date in series[key]:
                    raise ValueError(f"Duplicate arrival row: {observed_date}, {key}")
                series[key][observed_date] = value
    if mismatches:
        raise ValueError(f"Source has {mismatches} rows where components do not add to Total")
    dates = [day for values in series.values() for day in values]
    return series, {"rows": row_count, "arrival_rows": arrival_count,
                    "first_date": min(dates).isoformat(), "last_date": max(dates).isoformat(),
                    "arithmetic_mismatches": mismatches}


def choose_points(series: dict[tuple[str, str], dict[date, int]]) -> list[str]:
    """Choose ten well populated points by visitor arrivals in 2025 only."""
    totals: dict[str, int] = defaultdict(int)
    for (point, _group), values in series.items():
        if point in STRUCTURAL_BREAK_POINTS:
            continue
        days_2025 = [day for day in values if day.year == 2025]
        if len(days_2025) < 350:
            continue
        totals[point] += sum(values[day] for day in days_2025)
    if len(totals) < 10:
        raise ValueError("Fewer than 10 sufficiently observed control points")
    return sorted(totals, key=lambda point: (-totals[point], point))[:10]


def predict(values: dict[date, int], cutoff: date, target: date, method: str) -> float:
    """Forecast using observations strictly before the simulated release date."""
    last = cutoff - timedelta(days=1)
    same_weekday = last - timedelta(days=(last.weekday() - target.weekday()) % 7)
    count = {"last_week": 1, "weekday_mean4": 4, "weekday_median8": 8}[method]
    history = [values.get(same_weekday - timedelta(days=7 * i)) for i in range(count)]
    if any(value is None for value in history):
        raise ValueError(f"Missing historical weekday for {cutoff}, {target}, {method}")
    observed = [float(value) for value in history if value is not None]
    return statistics.median(observed) if method == "weekday_median8" else statistics.mean(observed)


def scale(values: dict[date, int], cutoff: date) -> float:
    """Compute the seasonal MASE denominator from known 2025 onward data."""
    errors = [abs(value - values[day - timedelta(days=7)])
              for day, value in values.items()
              if TRAIN_START <= day < cutoff and day - timedelta(days=7) in values]
    if not errors or statistics.mean(errors) == 0:
        raise ValueError(f"Invalid MASE scale for cutoff {cutoff}")
    return statistics.mean(errors)


def calibration_errors(values: dict[date, int], cutoff: date, method: str) -> list[float]:
    """Use earlier 15-day pseudo-rounds to calibrate the 70% interval."""
    errors: list[float] = []
    pseudo = cutoff - timedelta(days=182)
    while pseudo + timedelta(days=14) < cutoff:
        for horizon in range(1, 15):
            target = pseudo + timedelta(days=horizon)
            if target in values:
                errors.append(values[target] - predict(values, pseudo, target, method))
        pseudo += timedelta(days=7)
    if len(errors) < 100:
        raise ValueError(f"Insufficient interval calibration data at {cutoff}")
    return errors


def run() -> None:
    """Write per-observation predictions and aggregate scores."""
    series, source_info = read_arrivals()
    points = choose_points(series)
    OUTPUT.mkdir(exist_ok=True)
    predictions: list[dict[str, object]] = []
    for cutoff in CUTOFFS:
        for point in points:
            for group in GROUPS:
                values = series[(point, group)]
                denominator = scale(values, cutoff)
                for method in METHODS:
                    residuals = calibration_errors(values, cutoff, method)
                    low_offset = quantile(residuals, ALPHA / 2)
                    high_offset = quantile(residuals, 1 - ALPHA / 2)
                    for horizon in range(1, 15):
                        target = cutoff + timedelta(days=horizon)
                        if target not in values:
                            raise ValueError(f"Missing holdout observation: {target}, {point}")
                        forecast = predict(values, cutoff, target, method)
                        lower = max(0.0, forecast + low_offset)
                        upper = max(lower, forecast + high_offset)
                        actual = values[target]
                        winkler = upper - lower
                        if actual < lower:
                            winkler += 2 / ALPHA * (lower - actual)
                        elif actual > upper:
                            winkler += 2 / ALPHA * (actual - upper)
                        predictions.append({"cutoff": cutoff.isoformat(), "target_date": target.isoformat(),
                                            "horizon": horizon + 1, "point": point, "group": group,
                                            "method": method, "actual": actual, "forecast": round(forecast, 3),
                                            "lower_70": round(lower, 3), "upper_70": round(upper, 3),
                                            "scaled_absolute_error": abs(actual - forecast) / denominator,
                                            "covered": int(lower <= actual <= upper),
                                            "scaled_winkler": winkler / denominator})
    with (OUTPUT / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(predictions[0]))
        writer.writeheader()
        writer.writerows(predictions)
    scores = {}
    for method in METHODS:
        rows = [row for row in predictions if row["method"] == method]
        scores[method] = {"MASE": statistics.mean(row["scaled_absolute_error"] for row in rows),
                          "coverage_70": statistics.mean(row["covered"] for row in rows),
                          "mean_scaled_winkler": statistics.mean(row["scaled_winkler"] for row in rows),
                          "per_round_MASE": {cutoff.isoformat(): statistics.mean(
                              row["scaled_absolute_error"] for row in rows if row["cutoff"] == cutoff.isoformat())
                              for cutoff in CUTOFFS}}
    summary = {"source_url": SOURCE_URL, "source_file": SOURCE.name, "source_info": source_info,
               "selected_points": points, "selection_rule": "Top 10 by 2025 mainland plus other visitor arrivals among points with >=350 observed days in 2025",
               "excluded_for_structural_break": sorted(STRUCTURAL_BREAK_POINTS),
               "cutoffs": [day.isoformat() for day in CUTOFFS], "evaluated_days_per_round": 14,
               "series": len(points) * len(GROUPS), "prediction_rows": len(predictions), "scores": scores}
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
