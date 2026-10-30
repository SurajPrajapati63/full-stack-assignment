"""Plot average device temperatures from a summary JSON file."""

import argparse
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


def parse_arguments() -> argparse.Namespace:
    """Parse input JSON and chart output paths."""
    parser = argparse.ArgumentParser(description="Plot device temperatures.")
    parser.add_argument("--input", type=Path, default=Path("output/summary.json"))
    parser.add_argument(
        "--output", type=Path, default=Path("output/temperature_chart.png")
    )
    return parser.parse_args()


def load_summary(path: Path) -> tuple[float, list[dict[str, object]]]:
    """Load and validate threshold and device data from JSON."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object.")
    threshold = data.get("threshold")
    devices = data.get("devices")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError("JSON threshold must be a number.")
    if not math.isfinite(threshold):
        raise ValueError("JSON threshold must be finite.")
    if not isinstance(devices, list):
        raise ValueError("JSON devices must be a list.")
    if not devices:
        raise ValueError("Summary contains zero devices; no chart was created.")
    for device in devices:
        _validate_device(device)
    return float(threshold), devices


def _validate_device(device: object) -> None:
    """Reject device entries missing valid chart fields."""
    if not isinstance(device, dict):
        raise ValueError("Each device summary must be an object.")
    device_id = device.get("device_id")
    temperature = device.get("avg_temperature")
    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("Each device must have a non-blank device_id.")
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        raise ValueError(f"{device_id} has an invalid avg_temperature.")
    if not math.isfinite(temperature):
        raise ValueError(f"{device_id} has a non-finite avg_temperature.")


def create_chart(
    threshold: float, devices: list[dict[str, object]], output: Path
) -> None:
    """Draw and save a labeled temperature bar chart."""
    device_ids = [str(device["device_id"]) for device in devices]
    temperatures = [float(device["avg_temperature"]) for device in devices]
    figure, axis = plt.subplots(figsize=(max(8, len(devices) * 1.1), 5))
    bars = axis.bar(device_ids, temperatures, color="steelblue")
    axis.bar_label(bars, fmt="%.2f", padding=3)
    axis.axhline(
        threshold, color="darkorange", linestyle="--", label=f"Threshold ({threshold:g} °C)"
    )
    axis.set_title("Average Temperature by Device")
    axis.set_xlabel("Device")
    axis.set_ylabel("Average Temperature (°C)")
    axis.set_ylim(top=max(max(temperatures), threshold, 1.0) * 1.15)
    axis.legend()
    if len(devices) > 6:
        axis.tick_params(axis="x", labelrotation=45)
        for label in axis.get_xticklabels():
            label.set_ha("right")
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=150)
    plt.close(figure)


def main() -> int:
    """Load a summary and report chart-generation errors clearly."""
    args = parse_arguments()
    try:
        threshold, devices = load_summary(args.input)
        create_chart(threshold, devices, args.output)
    except FileNotFoundError:
        print(
            f"Error: Summary file not found: {args.input}. Run summarizer.py first.",
            file=sys.stderr,
        )
        return 1
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Temperature chart saved to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
