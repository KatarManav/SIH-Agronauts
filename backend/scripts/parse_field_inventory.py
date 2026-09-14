"""Parse the field-validated fixed-width landslide inventory.

The supplied file has a .csv extension but is a quoted, line-oriented export.
This parser keeps the original text because whitespace alignment is not a
stable substitute for a documented schema.
"""

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path


STATE_PATTERN = (
    r"Arunachal Pradesh|Assam|Manipur|Meghalaya|Mizoram|Nagaland|"
    r"Sikkim|Tripura|Himachal Pradesh|Uttarakhand|Jammu and Kashmir|"
    r"West Bengal|Odisha|Kerala|Maharashtra|Tamil Nadu|Karnataka|"
    r"Rajasthan|Gujarat|Bihar|Jharkhand|Chhattisgarh|Telangana|"
    r"Andhra Pradesh|Madhya Pradesh|Uttar Pradesh|Goa|Punjab|Haryana|"
    r"Delhi|Sikkim"
)
RECORD_START = re.compile(r'^"?\s*(\d+)\s+(.+?)\s*$')
STATE_RE = re.compile(rf"\b({STATE_PATTERN})\b", re.IGNORECASE)
COORDINATES_RE = re.compile(
    r"(?P<latitude>-?\d{1,2}(?:\.\d+)?)\s+"
    r"(?P<longitude>-?\d{2,3}(?:\.\d+)?)\b"
)
DATE_RE = re.compile(
    r"\b(?P<day>\d{1,2})\s+(?P<month>Jan(?:uary)?|Feb(?:ruary)?|"
    r"Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+(?P<year>20\d{2}|19\d{2})\b",
    re.IGNORECASE,
)


def clean_line(line: str) -> str:
    return line.strip().strip('"').strip()


def read_blocks(source: Path) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] | None = None
    with source.open(encoding="utf-8-sig", errors="replace") as handle:
        for raw_line in handle:
            line = clean_line(raw_line)
            if not line or line == "\x0c":
                continue
            match = RECORD_START.match(line)
            if match and match.group(1) != "0":
                if current is not None:
                    blocks.append(current)
                current = [line]
            elif current is not None:
                current.append(line)
    if current is not None:
        blocks.append(current)
    return blocks


def parse_block(lines: list[str], source_name: str) -> dict[str, str | float | None]:
    first = lines[0]
    number_match = RECORD_START.match(first)
    if number_match is None:
        raise ValueError(f"Unable to parse record start: {first[:80]}")
    serial_number = number_match.group(1)
    body = number_match.group(2)
    state_match = STATE_RE.search(body)
    coordinate_match = COORDINATES_RE.search(body)
    combined = " ".join(lines)
    event_date = None
    date_match = DATE_RE.search(combined)
    if date_match:
        try:
            event_date = datetime.strptime(
                f"{date_match.group('day')} {date_match.group('month')} "
                f"{date_match.group('year')}",
                "%d %B %Y",
            ).date().isoformat()
        except ValueError:
            for fmt in ("%d %b %Y",):
                try:
                    event_date = datetime.strptime(
                        f"{date_match.group('day')} {date_match.group('month')} "
                        f"{date_match.group('year')}",
                        fmt,
                    ).date().isoformat()
                    break
                except ValueError:
                    continue

    latitude = float(coordinate_match.group("latitude")) if coordinate_match else None
    longitude = float(coordinate_match.group("longitude")) if coordinate_match else None
    coordinates_valid = (
        latitude is not None
        and longitude is not None
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )
    return {
        "serial_number": serial_number,
        "slide_id": body.split()[0] if body.split() else None,
        "state": state_match.group(1) if state_match else None,
        "latitude": latitude if coordinates_valid else None,
        "longitude": longitude if coordinates_valid else None,
        "event_date": event_date,
        "has_event_date": bool(event_date),
        "source_file": source_name,
        "is_demo": False,
        "raw_record": combined,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "serial_number", "slide_id", "state", "latitude", "longitude",
        "event_date", "has_event_date", "source_file", "is_demo", "raw_record",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_inventory(source: Path, inventory_output: Path, events_output: Path, manifest: Path) -> dict:
    rows = [parse_block(block, source.name) for block in read_blocks(source)]
    dated_rows = [row for row in rows if row["has_event_date"] and row["latitude"] is not None]
    write_csv(inventory_output, rows)
    write_csv(events_output, dated_rows)
    summary = {
        "source_file": str(source),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "records": len(rows),
        "records_with_valid_coordinates": sum(
            row["latitude"] is not None and row["longitude"] is not None for row in rows
        ),
        "records_with_event_date": len(dated_rows),
        "state_counts": {},
        "outputs": [str(inventory_output), str(events_output)],
        "limitations": [
            "The source is a fixed-width text export with continuation lines.",
            "Only dates explicitly present in a record or continuation line are extracted.",
            "Undated records are spatial inventory evidence, not time-specific labels.",
            "Raw record text is retained for manual review.",
        ],
    }
    for row in rows:
        state = row["state"] or "UNKNOWN"
        summary["state_counts"][state] = summary["state_counts"].get(state, 0) + 1
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse the field-validated landslide inventory.")
    parser.add_argument("source", type=Path, nargs="?", default=Path("data/raw/landslide_report.csv"))
    parser.add_argument("--inventory-output", type=Path, default=Path("data/interim/field_validated_inventory.csv"))
    parser.add_argument("--events-output", type=Path, default=Path("data/interim/field_validated_dated_events.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/field_validated_inventory.json"))
    args = parser.parse_args()
    summary = parse_inventory(args.source, args.inventory_output, args.events_output, args.manifest)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
