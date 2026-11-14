"""Publish aggregate coverage for uniquely matched checkpoint media."""

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path


ROLES = ("text", "photo", "thumbnail", "video")
PLATFORMS = {"x", "weibo", "douyin", "instagram", "tiktok", "xiaohongshu"}
PORTS = {
    "airport": 1, "hzmb-hk-port": 2, "shenzhen-bay": 3, "lok-ma-chau-spur-line": 4,
    "lo-wu": 5, "man-kam-to": 6, "heung-yuen-wai": 7, "west-kowloon": 8,
    "china-ferry-terminal": 9, "macau-ferry-terminal": 10,
}


def export(inputs: list[Path], output: Path) -> None:
    """Count distinct encoded records per role using its own location evidence."""
    totals = {port: defaultdict(lambda: [set() for _ in ROLES]) for port in PORTS.values()}
    days = []
    for path in inputs:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                platform = row["platform"]
                if platform not in PLATFORMS:
                    raise ValueError(f"Unknown source platform: {platform}")
                days.append(row["publish_day_hkt"])
                for index, role in enumerate(ROLES):
                    if not row[f"{role}_available_at_utc"]:
                        continue
                    matches = json.loads(row.get(f"{role}_port_ids_json", row["port_ids_json"]))
                    if len(matches) == 1 and matches[0] in PORTS:
                        totals[PORTS[matches[0]]][platform][index].add(row["post_key"])
    result = {port: {platform: [len(records) for records in counts]
                     for platform, counts in sorted(platforms.items())}
              for port, platforms in totals.items()}
    summary = {"first": min(days), "last": max(days), "ports": result}
    output.write_text("window.CHECKPOINT_EVIDENCE = " + json.dumps(summary, separators=(",", ":")) + ";\n",
                      encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    export(args.index, args.out)
