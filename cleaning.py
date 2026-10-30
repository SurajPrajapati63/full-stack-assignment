"""Clean sensor readings into finite, bounded floating-point values."""

import math


def clean_sensor_readings(values: list | None) -> list[float]:
    """Keep valid non-negative readings and cap values at 500.0."""
    if not values:
        return []

    cleaned = []
    for value in values:
        if value is None or isinstance(value, bool):
            continue
        try:
            reading = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if not math.isfinite(reading) or reading < 0:
            continue
        cleaned.append(min(reading, 500.0))
    return cleaned
