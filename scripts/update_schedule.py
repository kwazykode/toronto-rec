#!/usr/bin/env python3
"""Build the tracker schedule from Toronto's weekly Drop-in Open Data file."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DATA_URL = (
    "https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/"
    "1a5be46a-4039-48cd-a2d2-8e702abf9516/resource/"
    "067b41e7-ac8a-4d3f-ad08-089f8cd70316/download/Drop-in.json"
)
CENTRES = {
    3643: "canoe",
    3732: "yonge",
    272: "stlawrence",
    63: "johninnes",
    3857: "eastbayfront",
}
SPORTS = ("pickleball", "badminton", "volleyball")
STATIC_END = "2026-09-06"
MIN_SESSION_COUNT = 5
MIN_SOURCE_SPAN_DAYS = 14
MIN_RETAINED_RATIO = 0.5
PREFIX = "window.TORONTO_REC_GENERATED = "


def fetch_rows(url: str = DATA_URL) -> list[dict]:
    request = urllib.request.Request(url, headers={"User-Agent": "toronto-rec-weekly-updater/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def load_rows(path: Path | None) -> list[dict]:
    if path is None:
        return fetch_rows()
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def parse_existing(path: Path) -> dict:
    if not path.exists():
        return {"updated": None, "sessions": []}
    text = path.read_text(encoding="utf-8").strip()
    if not text.startswith(PREFIX) or not text.endswith(";"):
        raise ValueError(f"{path} is not a recognized generated schedule file")
    return json.loads(text[len(PREFIX) : -1])


def is_tracked(row: dict) -> bool:
    title = str(row.get("Course Title", "")).lower()
    return (
        int(row.get("Location ID", -1)) in CENTRES
        and title.startswith(SPORTS)
        and str(row.get("Age Min")) == "19"
        and str(row.get("First Date", "")) > STATIC_END
    )


def clock_label(hour: int, minute: int) -> str:
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour:02d}:{minute:02d} {suffix}"


def access_for(section: str) -> str:
    lowered = section.lower()
    if "reserve a spot" in lowered:
        return "reserve"
    if "drop-in" in lowered:
        return "dropin"
    raise ValueError(f"Unrecognized access section: {section!r}")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def build_sessions(rows: list[dict]) -> list[dict]:
    source_locations = {int(row["Location ID"]) for row in rows if row.get("Location ID") is not None}
    missing = sorted(set(CENTRES) - source_locations)
    if missing:
        raise ValueError(f"City file is missing tracked location IDs: {missing}")

    grouped: dict[tuple, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    for row in rows:
        if not is_tracked(row):
            continue
        location_id = int(row["Location ID"])
        key = (
            location_id,
            str(row["First Date"]),
            str(row["Course Title"]).strip(),
            int(row["Start Hour"]),
            int(row["Start Minute"]),
            int(row["End Hour"]),
            int(row["End Min"]),
            str(row["DayOftheWeek"]).lower(),
        )
        access = access_for(str(row["Section"]))
        course_id = row.get("Course_ID")
        if access == "reserve":
            if not str(course_id).isdigit():
                raise ValueError(f"Reserve session has an invalid Course_ID: {course_id!r}")
            grouped[key][access].add(int(course_id))
        else:
            grouped[key][access]

    sessions = []
    for key, access_ids in grouped.items():
        location_id, date, name, start_hour, start_minute, end_hour, end_minute, day = key
        centre = CENTRES[location_id]
        start_key = f"{start_hour:02d}{start_minute:02d}"
        identifier = f"city-{centre}-{date}-{start_key}-{slug(name)}"
        access_values = set(access_ids)
        access = "both" if access_values == {"dropin", "reserve"} else next(iter(access_values))
        session = {
            "id": identifier,
            "centre": centre,
            "date": date,
            "name": name,
            "day": day,
            "time": (
                f"{clock_label(start_hour, start_minute)} - "
                f"{clock_label(end_hour, end_minute)}"
            ),
            "access": access,
        }
        if "reserve" in access_values:
            reserve_ids = access_ids["reserve"]
            if len(reserve_ids) != 1:
                raise ValueError(f"Session {identifier} has multiple reserve Course_ID values")
            session["reserveId"] = next(iter(reserve_ids))
        sessions.append(session)

    sessions.sort(key=lambda item: (item["date"], item["time"], item["centre"], item["name"]))
    validate_sessions(sessions)
    return sessions


def validate_sessions(sessions: list[dict]) -> None:
    if len(sessions) < MIN_SESSION_COUNT:
        raise ValueError(
            f"Only {len(sessions)} tracked sessions found; refusing a potentially incomplete update"
        )
    ids = [session["id"] for session in sessions]
    if len(ids) != len(set(ids)):
        raise ValueError("Generated session IDs are not unique")
    invalid_centres = sorted({s["centre"] for s in sessions} - set(CENTRES.values()))
    invalid_sports = sorted(
        {s.get("sport") or s["name"].lower().split()[0] for s in sessions} - set(SPORTS)
    )
    invalid_access = sorted({s["access"] for s in sessions} - {"dropin", "reserve", "both"})
    if invalid_centres or invalid_sports or invalid_access:
        raise ValueError(
            f"Invalid values: centres={invalid_centres}, sports={invalid_sports}, access={invalid_access}"
        )


def validate_fresh_sessions(fresh: list[dict], existing: list[dict]) -> None:
    validate_sessions(fresh)
    counts = Counter(session["centre"] for session in fresh)
    missing_centres = sorted(set(CENTRES.values()) - set(counts))
    if missing_centres:
        raise ValueError(f"No tracked sessions found for centres: {missing_centres}")

    dates = [date.fromisoformat(session["date"]) for session in fresh]
    source_span = (max(dates) - min(dates)).days
    if source_span < MIN_SOURCE_SPAN_DAYS:
        raise ValueError(
            f"City schedule covers only {source_span} days; expected at least {MIN_SOURCE_SPAN_DAYS}"
        )

    first_fresh_date = min(session["date"] for session in fresh)
    comparable_existing = [session for session in existing if session["date"] >= first_fresh_date]
    minimum_expected = len(comparable_existing) * MIN_RETAINED_RATIO
    if comparable_existing and len(fresh) < minimum_expected:
        raise ValueError(
            f"Session count fell from {len(comparable_existing)} to {len(fresh)}; manual review required"
        )


def merge_sessions(existing: list[dict], fresh: list[dict]) -> list[dict]:
    first_fresh_date = min(session["date"] for session in fresh)
    history = [session for session in existing if session["date"] < first_fresh_date]
    merged = history + fresh
    merged.sort(key=lambda item: (item["date"], item["time"], item["centre"], item["name"]))
    ids = [session["id"] for session in merged]
    if len(ids) != len(set(ids)):
        raise ValueError("Merged session IDs are not unique")
    return merged


def write_schedule(path: Path, payload: dict) -> None:
    rendered = PREFIX + json.dumps(payload, indent=2, ensure_ascii=False) + ";\n"
    path.write_text(rendered, encoding="utf-8")


def write_summary(path: Path, fresh: list[dict], merged: list[dict], updated: str) -> None:
    counts = defaultdict(int)
    for session in fresh:
        counts[session["centre"]] += 1
    first_date = min(session["date"] for session in fresh)
    last_date = max(session["date"] for session in fresh)
    lines = [
        "## Weekly schedule preview",
        "",
        f"- City data checked: **{updated}**",
        f"- Proposed source window: **{first_date} to {last_date}**",
        f"- Proposed sessions in current City file: **{len(fresh)}**",
        f"- Total generated sessions after preserving history: **{len(merged)}**",
        "",
        "### Sessions by centre",
        "",
    ]
    lines.extend(f"- {centre}: {counts[centre]}" for centre in CENTRES.values())
    lines.extend(
        [
            "",
            "Review the attached `schedule-data.js` artifact. Nothing has been committed or published.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="Read City JSON from a local fixture")
    parser.add_argument("--output", type=Path, default=Path("schedule-data.js"))
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--validate-file", type=Path)
    args = parser.parse_args()

    if args.validate_file:
        payload = parse_existing(args.validate_file)
        validate_sessions(payload["sessions"])
        print(f"Validated {len(payload['sessions'])} sessions in {args.validate_file}")
        return

    rows = load_rows(args.input)
    existing = parse_existing(args.output)
    fresh = build_sessions(rows)
    validate_fresh_sessions(fresh, existing.get("sessions", []))
    merged = merge_sessions(existing.get("sessions", []), fresh)
    updated = datetime.now(ZoneInfo("America/Toronto")).date().isoformat()
    write_schedule(args.output, {"updated": updated, "sessions": merged})
    if args.summary:
        write_summary(args.summary, fresh, merged, updated)
    print(f"Generated {len(fresh)} current and {len(merged)} total sessions")


if __name__ == "__main__":
    main()
