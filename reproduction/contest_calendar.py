"""Published Mainland and Hong Kong calendars for the tourism forecasts."""

from datetime import date, timedelta

# Each Mainland tuple is (event, start, end, alignment date).
MAINLAND = {
    2023: [
        ("qingming", "04-05", "04-05", "04-05"), ("may", "04-29", "05-03", "05-01"),
        ("dragon", "06-22", "06-24", "06-22"), ("national", "09-29", "10-06", "10-01"),
    ],
    2024: [
        ("newyear", "01-01", "01-01", "01-01"), ("lunar", "02-10", "02-17", "02-10"),
        ("qingming", "04-04", "04-06", "04-04"), ("may", "05-01", "05-05", "05-01"),
        ("dragon", "06-08", "06-10", "06-10"), ("midautumn", "09-15", "09-17", "09-17"),
        ("national", "10-01", "10-07", "10-01"),
    ],
    2025: [
        ("newyear", "01-01", "01-01", "01-01"), ("lunar", "01-28", "02-04", "01-29"),
        ("qingming", "04-04", "04-06", "04-04"), ("may", "05-01", "05-05", "05-01"),
        ("dragon", "05-31", "06-02", "05-31"), ("national", "10-01", "10-08", "10-01"),
    ],
    2026: [
        ("newyear", "01-01", "01-03", "01-01"), ("lunar", "02-15", "02-23", "02-17"),
        ("qingming", "04-04", "04-06", "04-05"), ("may", "05-01", "05-05", "05-01"),
        ("dragon", "06-19", "06-21", "06-19"), ("midautumn", "09-25", "09-27", "09-25"),
        ("national", "10-01", "10-07", "10-01"),
    ],
    2027: [
        ("newyear", "01-01", "01-03", "01-01"), ("lunar", "02-05", "02-13", "02-06"),
        ("qingming", "04-03", "04-05", "04-05"), ("may", "05-01", "05-05", "05-01"),
        ("dragon", "06-09", "06-09", "06-09"), ("midautumn", "09-15", "09-15", "09-15"),
        ("national", "10-01", "10-07", "10-01"),
    ],
}
WORKDAY = {
    2023: "04-23 05-06 06-25 10-07 10-08",
    2024: "02-04 02-18 04-07 04-28 05-11 09-14 09-29 10-12",
    2025: "01-26 02-08 04-27 09-28 10-11",
    2026: "01-04 02-14 02-28 05-09 09-20 10-10",
    2027: "01-31 02-14 05-08 09-26 10-09",
}
HK_HOLIDAYS = {
    2023: "04-05 04-07 04-08 04-10 05-01 05-26 06-22 07-01 09-30 10-02 10-23 12-25 12-26",
    2024: "01-01 02-10 02-12 02-13 03-29 03-30 04-01 04-04 05-01 05-15 06-10 07-01 09-18 10-01 10-11 12-25 12-26",
    2025: "01-01 01-29 01-30 01-31 04-04 04-18 04-19 04-21 05-01 05-05 05-31 07-01 10-01 10-07 10-29 12-25 12-26",
    2026: "01-01 02-17 02-18 02-19 04-03 04-04 04-06 04-07 05-01 05-25 06-19 07-01 09-26 10-01 10-19 12-25 12-26",
    2027: "01-01 02-06 02-08 02-09 03-26 03-27 03-29 04-05 05-01 05-13 06-09 07-01 09-16 10-01 10-08 12-25 12-27",
}
EASTER = {2023: ("04-07", "04-10"), 2024: ("03-29", "04-01"),
          2025: ("04-18", "04-21"), 2026: ("04-03", "04-07"), 2027: ("03-26", "03-29")}
MAJOR = {"lunar", "may", "national", "easter", "xmas"}


def dates_by_year(mapping: dict[int, str]) -> set[date]:
    """Expand the annual date lists."""
    return {date.fromisoformat(f"{year}-{day}") for year, days in mapping.items() for day in days.split()}


def event_dates() -> tuple[dict[date, tuple[str, int]], set[date], dict[tuple[str, int], list[date]]]:
    """Label event days, the two days on each side, and historical analogs."""
    event = {}
    rank = {}
    mainland_days = set()
    analogs = {}
    for year, mainland in MAINLAND.items():
        easter_start, easter_end = EASTER[year]
        periods = [(name, start, end, anchor, True) for name, start, end, anchor in mainland]
        periods.extend([
            ("easter", easter_start, easter_end, easter_start, False),
            ("xmas", "12-24", "12-26", "12-25", False),
        ])
        for name, start, end, anchor, is_mainland in periods:
            first, last, anchor_day = [date.fromisoformat(f"{year}-{day}") for day in (start, end, anchor)]
            for offset in range(-2, (last - first).days + 3):
                day = first + timedelta(days=offset)
                active = first <= day <= last
                if active and is_mainland:
                    mainland_days.add(day)
                key = (name, (day - anchor_day).days)
                analogs.setdefault(key, []).append(day)
                priority = (active, name in MAJOR, is_mainland)
                if day not in rank or priority > rank[day]:
                    event[day] = key
                    rank[day] = priority
    return event, mainland_days, analogs
