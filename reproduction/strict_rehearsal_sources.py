"""Recover each noon release used by the five-round historical rehearsal."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
import hashlib
import json
from pathlib import Path

from backtest import SOURCE_URL, read_arrivals
from hk_open_data_archive import HKT, archive_time, archive_url, curl, versions


OFFICIAL_ORIGINS = tuple(map(date.fromisoformat, (
    "2026-12-14", "2027-01-12", "2027-02-17", "2027-03-18", "2027-04-16",
)))
HISTORICAL_ORIGINS = tuple(day.replace(year=day.year - 1) for day in OFFICIAL_ORIGINS)
HISTORICAL_PRETRAINING_DAY = date(2025, 11, 30)


def sha256(path):
    with path.open("rb") as handle:
        digest = hashlib.sha256()
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def noon(day):
    return datetime.combine(day, time(12), HKT)


def vintage(release_day, available):
    timestamps = [
        version for version in available
        if version.startswith(release_day.strftime("%Y%m%d") + "-")
        and datetime.fromisoformat(archive_time(version)) <= noon(release_day)
    ]
    if not timestamps:
        raise ValueError(f"No archived snapshot on {release_day} by noon HKT")
    version = max(timestamps)
    return {
        "release_noon_hkt": noon(release_day).isoformat(), "archive_at_hkt": archive_time(version),
        "archive_version": version, "history_end": (release_day - timedelta(days=1)).isoformat(),
        "archive_url": archive_url("get-file", SOURCE_URL, time=version),
        "file": f"raw/immd-arrivals-{version}.csv",
    }


def select_releases(round_number, origin):
    start = origin - timedelta(days=2)
    available = versions(SOURCE_URL, start, origin)
    release_rows = []
    for number in range(1, 4):
        release_day = start + timedelta(days=number - 1)
        release_rows.append({
            "round": round_number, "release": number, "origin": origin.isoformat(),
            "official_origin": OFFICIAL_ORIGINS[round_number - 1].isoformat(),
            **vintage(release_day, available),
        })
    return release_rows


def download(root, item):
    destination = root / item["file"]
    path = destination
    if not path.exists():
        path = destination.with_suffix(".part")
        path.write_bytes(curl(item["archive_url"]))
    _, info = read_arrivals(path)
    if info["last_date"] != item["history_end"] or info["rows"] < 40_000:
        raise ValueError(f"{item['archive_version']} has unexpected observations: {info}")
    if path != destination:
        path.replace(destination)
    return {**item, "bytes": destination.stat().st_size, "sha256": sha256(destination), "source_info": info}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--archive-dir", required=True, type=Path)
    args = cli.parse_args()
    root = args.archive_dir
    (root / "raw").mkdir(parents=True, exist_ok=True)
    pre_day = HISTORICAL_PRETRAINING_DAY
    pretraining = download(root, vintage(pre_day, versions(SOURCE_URL, pre_day, pre_day)))
    print("Pretraining release", pretraining["archive_version"], flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(select_releases, number, origin)
                for number, origin in enumerate(HISTORICAL_ORIGINS, 1)]
        releases = [row for job in jobs for row in job.result()]
        jobs = [pool.submit(download, root, row) for row in releases]
        completed = []
        for job in jobs:
            row = job.result()
            completed.append(row)
            print(row["archive_version"], "history through", row["history_end"], row["bytes"], flush=True)
    path = root / "archive_manifest.json"
    manifest = {"source_url": SOURCE_URL, "pretraining_release": pretraining, "releases": completed}
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Archived and verified the pretraining release and {len(completed)} round releases.", flush=True)


if __name__ == "__main__":
    main()
