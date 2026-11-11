"""Check public data releases and refresh the dashboard's source status."""

import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

PAGE = "https://tourismforecasting.net/tfc/data_release.html"
PASSENGERS = "https://www.immd.gov.hk/opendata/eng/transport/immigration_clearance/statistics_on_daily_passenger_traffic.csv"
HKT = timezone(timedelta(hours=8))


class ReleaseItems(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if tag == "li" and "release-item" in fields.get("class", "").split():
            self.current = {"text": [], "links": []}
        if tag == "a" and self.current is not None and fields.get("href"):
            self.current["links"].append(urljoin(PAGE, fields["href"]))

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "li" and self.current is not None:
            self.items.append((" ".join(self.current["text"]).strip(), self.current["links"]))
            self.current = None


def fetch(url):
    try:
        with urlopen(Request(url, headers={"User-Agent": "HK-Arrivals-Outlook/1.0"}), timeout=22) as response:
            body = response.read(32_000_001)
    except OSError:
        if sys.platform != "win32":
            raise
        result = subprocess.run(
            ["curl.exe", "--ssl-no-revoke", "-4", "-fsSL", "--connect-timeout", "12", "--max-time", "80", url],
            capture_output=True, timeout=84, check=True,
        )
        body = result.stdout
    if not body or len(body) > 32_000_000:
        raise ValueError("empty or oversized response")
    return body


def store(archive, name, data):
    if archive is None:
        return
    archive.mkdir(parents=True, exist_ok=True)
    original = Path(name)
    digest = hashlib.sha256(data).hexdigest()[:16]
    output = archive / f"{original.stem}-{digest}{original.suffix}"
    if not output.exists():
        temporary = output.with_suffix(output.suffix + ".part")
        temporary.write_bytes(data)
        temporary.replace(output)


def organizer(archive):
    html = fetch(PAGE)
    parser = ReleaseItems()
    parser.feed(html.decode("utf-8-sig"))
    if len(parser.items) != 21:
        raise ValueError("The organizer changed the release page structure")
    templates = []
    database = False
    failures = 0
    for title, urls in parser.items:
        workbook_links = [
            url for url in urls if urlsplit(url).scheme == "https"
            and urlsplit(url).netloc == urlsplit(PAGE).netloc
            and Path(urlsplit(url).path).suffix.lower() in {".xlsx", ".csv", ".zip", ".xls"}
        ]
        if not workbook_links:
            continue
        round_id = re.search(r"Round\s+(\d)\s+Submission Template", title, re.I)
        if round_id:
            templates.append(int(round_id.group(1)))
        if "database release" in title.casefold():
            database = True
        for url in workbook_links if archive is not None else ():
            try:
                data = fetch(url)
                suffix = Path(urlsplit(url).path).suffix.lower()
                if suffix in {".xlsx", ".zip"} and not data.startswith(b"PK\x03\x04"):
                    raise ValueError("Expected an Excel or ZIP container")
                if suffix == ".xls" and not data.startswith(b"\xd0\xcf\x11\xe0"):
                    raise ValueError("Expected a binary Excel workbook")
                if data.lstrip().startswith(b"<"):
                    raise ValueError("Received HTML in place of a download")
                store(archive, Path(urlsplit(url).path).name, data)
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                print(f"Organizer download unavailable: {url} ({type(error).__name__})", file=sys.stderr)
                failures += 1
    return database, sorted(set(templates)), failures


def passengers(archive):
    data = fetch(PASSENGERS)
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    required = {"Date", "Control Point", "Arrival / Departure", "Mainland Visitors", "Other Visitors"}
    if not required.issubset(reader.fieldnames or ()):
        raise ValueError("Unexpected passenger data columns")
    dates = [datetime.strptime(row["Date"], "%d-%m-%Y").date() for row in reader if row["Arrival / Departure"] == "Arrival"]
    if len(dates) < 20_000 or min(dates).year > 2021:
        raise ValueError("Incomplete arrivals dataset")
    store(archive, "immd-daily-passengers.csv", data)
    return {"through": max(dates).isoformat(), "arrivalRows": len(dates)}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "site" / "sources.js")
    cli.add_argument("--archive", type=Path)
    cli.add_argument("--allow-partial", action="store_true")
    args = cli.parse_args()
    status = {
        "checkedAt": datetime.now(HKT).strftime("%Y-%m-%d %H:%M (UTC+8)"),
        "database": False, "templateRounds": [], "organizerError": False, "passengers": None,
    }
    failures = 0
    try:
        status["database"], status["templateRounds"], failures = organizer(args.archive)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        print(f"Organizer page unavailable: {type(error).__name__}", file=sys.stderr)
        status["organizerError"] = True
    try:
        status["passengers"] = passengers(args.archive)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        print(f"Public passenger source unavailable: {type(error).__name__}", file=sys.stderr)
    if not args.allow_partial and (status["organizerError"] or failures):
        sys.exit("Release check incomplete. Previous source status preserved.")
    output = args.out.with_suffix(".tmp")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("window.SOURCES = " + json.dumps(status) + ";\n", encoding="utf-8")
    output.replace(args.out)
    print(json.dumps(status))


if __name__ == "__main__":
    main()
