"""Tests for sensor-reading cleanup."""

import math

from cleaning import clean_sensor_readings


def test_cleans_mixed_input_in_original_order() -> None:
    """Discard invalid values and preserve the order of valid readings."""
    assert clean_sensor_readings(
        ["23.5", None, -1, "abc", 700, 45, "  12 "]
    ) == [23.5, 500.0, 45.0, 12.0]


def test_empty_list_returns_empty_list() -> None:
    """Return no readings for an empty input."""
    assert clean_sensor_readings([]) == []


def test_all_invalid_values_return_empty_list() -> None:
    """Return no readings when every input is invalid."""
    assert clean_sensor_readings([None, "abc", -1, math.nan, math.inf]) == []


def test_clips_values_above_the_boundary() -> None:
    """Keep the boundary and cap only values above it."""
    assert clean_sensor_readings([499.9, 500.0, 500.1]) == [499.9, 500.0, 500.0]


def test_keeps_zero_and_drops_negative_values() -> None:
    """Treat zero as valid while dropping negative readings."""
    assert clean_sensor_readings([0, -0.01]) == [0.0]


def test_drops_non_finite_values_and_booleans() -> None:
    """Reject NaN, infinities, and booleans."""
    assert clean_sensor_readings([math.nan, math.inf, -math.inf, True, False]) == []


def test_does_not_mutate_input() -> None:
    """Leave the original list unchanged."""
    values = ["1", None, 700]
    original = values.copy()

    clean_sensor_readings(values)

    assert values == original
