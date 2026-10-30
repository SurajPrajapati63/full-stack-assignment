"""Summarize device telemetry from a CSV file."""

import argparse
import csv
import json
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from cleaning import clean_sensor_readings

REQUIRED_COLUMNS = frozenset({"device_id", "status", "temperature"})
VALID_STATUSES = frozenset({"ACTIVE", "WARNING", "ERROR"})
LOGGER = logging.getLogger(__name__)


@dataclass
class DeviceTotals:
    """Track accumulated telemetry counts and temperatures for one device."""

    total_records: int = 0
    temperature_sum: float = 0.0
    error_count: int = 0


class SummarizerError(Exception):
    """Represent an expected input or output problem."""


def read_rows(path: Path) -> list[tuple[int, dict[str, str | None]]]:
    """Read CSV rows and validate the file structure."""
    try:
        if path.is_dir():
            raise SummarizerError(f"Input path is a directory: {path}")
        with path.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                raise SummarizerError(f"Input file is empty: {path}")
            missing = REQUIRED_COLUMNS.difference(reader.fieldnames)
            if missing:
                names = ", ".join(sorted(missing))
                raise SummarizerError(f"Missing required columns: {names}")
            rows = [(reader.line_num, row) for row in reader]
    except UnicodeDecodeError as error:
        raise SummarizerError(f"Input file is not valid UTF-8 text: {path}") from error
    except OSError as error:
        raise SummarizerError(f"Cannot read input file {path}: {error}") from error
    if not rows:
        raise SummarizerError(f"Input file has no data rows: {path}")
    return rows


def validate_row(
    row: dict[str, str | None], line_no: int
) -> dict[str, str | float] | None:
    """Normalize a valid row or log why it should be skipped."""
    device_id = (row.get("device_id") or "").strip()
    if not device_id:
        LOGGER.warning("Skipping row %d: device_id is missing or blank", line_no)
        return None

    status = (row.get("status") or "").strip().upper()
    if status not in VALID_STATUSES:
        LOGGER.warning("Skipping row %d: status is blank or invalid", line_no)
        return None

    temperature_value = row.get("temperature")
    readings = clean_sensor_readings([temperature_value])
    if not readings:
        LOGGER.warning("Skipping row %d: temperature is missing or invalid", line_no)
        return None
    if float(temperature_value) > 500.0:
        LOGGER.warning(
            "Row %d: temperature %s capped to 500.0", line_no, temperature_value
        )

    return {
        "device_id": device_id,
        "status": status,
        "temperature": readings[0],
    }


def aggregate(
    rows: list[dict[str, str | float]]
) -> list[dict[str, str | int | float]]:
    """Aggregate valid rows into sorted per-device summaries."""
    grouped: dict[str, DeviceTotals] = {}
    for row in rows:
        device_id = str(row["device_id"])
        entry = grouped.get(device_id)
        if entry is None:
            entry = DeviceTotals()
            grouped[device_id] = entry
        entry.total_records += 1
        entry.temperature_sum += float(row["temperature"])
        if row["status"] == "ERROR":
            entry.error_count += 1

    return [
        _build_summary(device_id, entry)
        for device_id, entry in sorted(grouped.items())
    ]


def _build_summary(
    device_id: str, totals: DeviceTotals
) -> dict[str, str | int | float]:
    """Create one rounded summary from a device's accumulated totals."""
    return {
        "device_id": device_id,
        "total_records": totals.total_records,
        "avg_temperature": totals.temperature_sum / totals.total_records,
        "error_count": totals.error_count,
    }


def _validate_rows(
    source_rows: list[tuple[int, dict[str, str | None]]]
) -> tuple[list[dict[str, str | float]], int]:
    """Validate all source rows and return accepted rows and skip count."""
    valid_rows = []
    for line_no, row in source_rows:
        normalized = validate_row(row, line_no)
        if normalized is not None:
            valid_rows.append(normalized)
    return valid_rows, len(source_rows) - len(valid_rows)


def filter_devices(
    summaries: list[dict[str, str | int | float]], threshold: float
) -> list[dict[str, str | int | float]]:
    """Keep devices at or below the temperature threshold."""
    return [
        summary
        for summary in summaries
        if float(summary["avg_temperature"]) <= threshold
    ]


def round_summaries(
    summaries: list[dict[str, str | int | float]]
) -> list[dict[str, str | int | float]]:
    """Round averages for display and export without changing source summaries."""
    return [
        {**summary, "avg_temperature": round(float(summary["avg_temperature"]), 2)}
        for summary in summaries
    ]


def write_json(
    summaries: list[dict[str, str | int | float]], path: Path, threshold: float
) -> None:
    """Write threshold and device summaries as formatted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump({"threshold": threshold, "devices": summaries}, file, indent=2)
        file.write("\n")


def print_table(summaries: list[dict[str, str | int | float]]) -> None:
    """Print device summaries in an aligned terminal table."""
    print(f"{'DEVICE_ID':<12}{'RECORDS':>9}{'AVG_TEMP':>11}{'ERRORS':>9}")
    for summary in summaries:
        print(
            f"{str(summary['device_id']):<12}"
            f"{int(summary['total_records']):>9}"
            f"{float(summary['avg_temperature']):>11.2f}"
            f"{int(summary['error_count']):>9}"
        )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="Summarize device telemetry.")
    parser.add_argument("--input", type=Path, default=Path("device_telemetry.csv"))
    parser.add_argument("--output", type=Path, default=Path("output/summary.json"))
    parser.add_argument("--threshold", type=float, default=80.0)
    return parser.parse_args()


def main() -> int:
    """Run the CSV summarization pipeline and report expected errors."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    args = parse_arguments()
    if not math.isfinite(args.threshold):
        # A bad threshold is an argument error (2); input and file errors return 1.
        print("Error: threshold must be a finite number.", file=sys.stderr)
        return 2
    try:
        source_rows = read_rows(args.input)
        valid_rows, skipped = _validate_rows(source_rows)
        if not valid_rows:
            raise SummarizerError("Every data row is invalid; no devices were produced.")
        all_summaries = aggregate(valid_rows)
        summaries = filter_devices(all_summaries, args.threshold)
        removed = len(all_summaries) - len(summaries)
        display_summaries = round_summaries(summaries)
        write_json(display_summaries, args.output, args.threshold)
    except (SummarizerError, OSError, csv.Error, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print_table(display_summaries)
    print(
        f"Rows read: {len(source_rows)} | Rows valid: {len(valid_rows)} "
        f"| Rows skipped: {skipped} | Devices removed by filter: {removed}"
    )
    if not summaries:
        print("No devices remain after filtering; an empty summary was written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
