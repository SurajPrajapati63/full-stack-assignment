"""Tests for summary validation and temperature chart generation."""

import json
import sys
from pathlib import Path

import pytest

from plot_temperatures import load_summary, main


@pytest.mark.parametrize(
    "content",
    [
        [],
        {"threshold": 80.0, "devices": {}},
        {"threshold": 80.0, "devices": []},
        {
            "threshold": 80.0,
            "devices": [{"device_id": "DEV_A", "avg_temperature": "warm"}],
        },
    ],
    ids=["root-not-object", "devices-not-list", "no-devices", "bad-temperature"],
)
def test_load_summary_rejects_malformed_structure(
    tmp_path: Path, content: object
) -> None:
    """Reject malformed summary shape and device temperature values."""
    source = tmp_path / "summary.json"
    source.write_text(json.dumps(content), encoding="utf-8")

    with pytest.raises(ValueError):
        load_summary(source)


def test_main_missing_json_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Report the friendly missing-summary message without a traceback."""
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(sys, "argv", ["plot_temperatures.py", "--input", str(missing)])

    assert main() == 1
    assert capsys.readouterr().err.strip() == (
        f"Error: Summary file not found: {missing}. Run summarizer.py first."
    )


def test_main_creates_png_for_valid_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Create a chart PNG from a valid JSON summary."""
    source = tmp_path / "summary.json"
    output = tmp_path / "charts" / "temperatures.png"
    source.write_text(
        json.dumps(
            {
                "threshold": 80.0,
                "devices": [{"device_id": "DEV_A", "avg_temperature": 55.25}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys, "argv", ["plot_temperatures.py", "--input", str(source), "--output", str(output)]
    )

    assert main() == 0
    assert output.is_file()
    assert output.stat().st_size > 0
