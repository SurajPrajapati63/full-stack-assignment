"""Tests for CSV aggregation and JSON export."""

import json
import sys
from pathlib import Path

import pytest

from summarizer import (
    SummarizerError,
    aggregate,
    filter_devices,
    main,
    read_rows,
    validate_row,
    write_json,
)


def test_aggregation_calculates_counts_average_and_errors() -> None:
    """Aggregate temperature and error counts per device."""
    rows = [
        {"device_id": "DEV_B", "status": "ERROR", "temperature": 70.0},
        {"device_id": "DEV_A", "status": "ACTIVE", "temperature": 60.0},
        {"device_id": "DEV_B", "status": "ACTIVE", "temperature": 90.0},
    ]

    assert aggregate(rows) == [
        {
            "device_id": "DEV_A",
            "total_records": 1,
            "avg_temperature": 60.0,
            "error_count": 0,
        },
        {
            "device_id": "DEV_B",
            "total_records": 2,
            "avg_temperature": 80.0,
            "error_count": 1,
        },
    ]


def test_threshold_filter_keeps_exact_boundary() -> None:
    """Remove only summaries strictly above the threshold."""
    summaries = [
        {"device_id": "DEV_A", "total_records": 1, "avg_temperature": 80.0, "error_count": 0},
        {"device_id": "DEV_B", "total_records": 1, "avg_temperature": 80.01, "error_count": 0},
    ]

    assert filter_devices(summaries, 80.0) == summaries[:1]


def test_threshold_filter_uses_unrounded_average() -> None:
    """Remove a value above the threshold even if display rounding would hide it."""
    summaries = aggregate(
        [
            {"device_id": "DEV_A", "status": "ACTIVE", "temperature": 80.0},
            {"device_id": "DEV_B", "status": "ACTIVE", "temperature": 80.004},
            {"device_id": "DEV_B", "status": "ACTIVE", "temperature": 80.004},
        ]
    )

    assert filter_devices(summaries, 80.0) == [
        {
            "device_id": "DEV_A",
            "total_records": 1,
            "avg_temperature": 80.0,
            "error_count": 0,
        }
    ]


def test_validate_row_normalizes_status_and_skips_bad_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Normalize case-insensitive statuses and warn for invalid rows."""
    valid = validate_row(
        {"device_id": " DEV_A ", "status": " error ", "temperature": "21.5"}, 2
    )
    invalid = validate_row(
        {"device_id": "DEV_A", "status": "ACTIVE", "temperature": "N/A"}, 3
    )

    assert valid == {
        "device_id": "DEV_A",
        "status": "ERROR",
        "temperature": 21.5,
    }
    assert invalid is None
    assert "row 3" in caplog.text


def test_validate_row_warns_when_temperature_is_capped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Warn about a capped reading while accepting its capped value."""
    valid = validate_row(
        {"device_id": "DEV_A", "status": "ACTIVE", "temperature": "700"}, 7
    )

    assert valid is not None
    assert valid["temperature"] == 500.0
    assert "Row 7: temperature 700 capped to 500.0" in caplog.text


def test_read_rows_reports_missing_file(tmp_path: Path) -> None:
    """Raise a clear input error for a missing CSV."""
    with pytest.raises(SummarizerError, match="Cannot read input file"):
        read_rows(tmp_path / "missing.csv")


def test_read_rows_reports_missing_column(tmp_path: Path) -> None:
    """Name required columns absent from the CSV header."""
    source = tmp_path / "telemetry.csv"
    source.write_text("device_id,status\nDEV_A,ACTIVE\n", encoding="utf-8")

    with pytest.raises(SummarizerError, match="temperature"):
        read_rows(source)


def test_read_rows_reports_empty_file(tmp_path: Path) -> None:
    """Reject a CSV with no header or data."""
    source = tmp_path / "telemetry.csv"
    source.write_text("", encoding="utf-8")

    with pytest.raises(SummarizerError, match="empty"):
        read_rows(source)


def test_read_rows_handles_utf8_bom(tmp_path: Path) -> None:
    """Read the first header correctly when a CSV includes a UTF-8 BOM."""
    source = tmp_path / "bom.csv"
    source.write_text(
        "device_id,status,temperature\nDEV_A,ACTIVE,20\n", encoding="utf-8-sig"
    )

    assert read_rows(source) == [
        (2, {"device_id": "DEV_A", "status": "ACTIVE", "temperature": "20"})
    ]


def test_read_rows_header_only_file_raises(tmp_path: Path) -> None:
    """Reject a CSV containing a header but no data rows."""
    source = tmp_path / "header-only.csv"
    source.write_text("device_id,status,temperature\n", encoding="utf-8")

    with pytest.raises(SummarizerError, match="no data rows"):
        read_rows(source)


def test_read_rows_reports_invalid_utf8(tmp_path: Path) -> None:
    """Report a clear error for binary or otherwise invalid UTF-8 input."""
    source = tmp_path / "binary.csv"
    source.write_bytes(b"\xff\xfe\x00")

    with pytest.raises(SummarizerError) as error:
        read_rows(source)
    assert str(error.value) == f"Input file is not valid UTF-8 text: {source}"


def test_validate_row_rejects_unknown_status_and_blank_device_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Reject unknown statuses and rows without a device identifier."""
    unknown_status = validate_row(
        {"device_id": "DEV_A", "status": "UNKNOWN", "temperature": "20"}, 2
    )
    blank_device = validate_row(
        {"device_id": "  ", "status": "ACTIVE", "temperature": "20"}, 3
    )

    assert unknown_status is None
    assert blank_device is None
    assert "row 2" in caplog.text
    assert "row 3" in caplog.text


def test_main_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Summarize a CSV and write the expected JSON through the CLI."""
    source, output = tmp_path / "input.csv", tmp_path / "output" / "summary.json"
    source.write_text(
        "device_id,status,temperature\nDEV_A,ACTIVE,60.001\n"
        "DEV_A,ERROR,65.004\nDEV_B,ACTIVE,81\n",
        encoding="utf-8",
    )
    arguments = ["summarizer.py", "--input", str(source), "--output", str(output)]
    monkeypatch.setattr(sys, "argv", arguments)

    assert main() == 0
    assert "62.50" in capsys.readouterr().out
    expected_device = {
        "device_id": "DEV_A",
        "total_records": 2,
        "avg_temperature": 62.5,
        "error_count": 1,
    }
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "threshold": 80.0,
        "devices": [expected_device],
    }


def test_main_all_rows_invalid_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Return a clean error when every CSV row is invalid."""
    source = tmp_path / "invalid.csv"
    source.write_text(
        "device_id,status,temperature\nDEV_A,UNKNOWN,20\n", encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["summarizer.py", "--input", str(source)])

    assert main() == 1
    captured = capsys.readouterr()
    assert "Every data row is invalid" in captured.err
    assert "Traceback" not in captured.err


def test_main_missing_file_returns_1_without_traceback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Return a clean error for a missing CSV file."""
    missing = tmp_path / "missing.csv"
    monkeypatch.setattr(sys, "argv", ["summarizer.py", "--input", str(missing)])

    assert main() == 1
    captured = capsys.readouterr()
    assert str(missing) in captured.err
    assert "Traceback" not in captured.err


def test_main_invalid_threshold_returns_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Return an argument-error code for a non-finite threshold."""
    monkeypatch.setattr(sys, "argv", ["summarizer.py", "--threshold", "nan"])

    assert main() == 2
    assert "threshold must be a finite number" in capsys.readouterr().err


def test_main_empty_after_filter_writes_empty_devices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Write an empty device list when all valid devices exceed the threshold."""
    source = tmp_path / "hot.csv"
    output = tmp_path / "summary.json"
    source.write_text(
        "device_id,status,temperature\nDEV_A,ACTIVE,81\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "summarizer.py",
            "--input",
            str(source),
            "--output",
            str(output),
            "--threshold",
            "80",
        ],
    )

    assert main() == 0
    assert json.loads(output.read_text(encoding="utf-8")) == {
        "threshold": 80.0,
        "devices": [],
    }


def test_write_json_has_expected_shape(tmp_path: Path) -> None:
    """Export the threshold and summaries with the required JSON structure."""
    output = tmp_path / "nested" / "summary.json"
    summaries = [
        {
            "device_id": "DEV_A",
            "total_records": 2,
            "avg_temperature": 62.35,
            "error_count": 1,
        }
    ]

    write_json(summaries, output, 80.0)

    assert json.loads(output.read_text(encoding="utf-8")) == {
        "threshold": 80.0,
        "devices": summaries,
    }
