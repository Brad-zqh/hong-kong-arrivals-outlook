"""Read versioned public files from Hong Kong's open data archive."""

from datetime import datetime, timedelta, timezone
import json
import subprocess
import sys
from urllib.parse import urlencode


HKT = timezone(timedelta(hours=8))
ARCHIVE = "https://app.data.gov.hk/v1/historical-archive/"


def curl(url):
    executable = ["curl.exe", "--ssl-no-revoke"] if sys.platform == "win32" else ["curl"]
    cmd = [*executable, "-4", "-LsSf", "--connect-timeout", "10", "--max-time", "25",
           "--retry", "2", "--retry-max-time", "50", url]
    return subprocess.run(cmd, check=True, capture_output=True).stdout


def archive_url(endpoint, url, **params):
    return ARCHIVE + endpoint + "?" + urlencode({"url": url, **params})


def versions(url, start, end):
    body = curl(archive_url(
        "list-file-versions", url, start=start.strftime("%Y%m%d"), end=end.strftime("%Y%m%d")
    ))
    return json.loads(body)["timestamps"]


def archive_time(version):
    return datetime.strptime(version, "%Y%m%d-%H%M").replace(tzinfo=HKT).isoformat()
