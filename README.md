# device-log-summarizer

A small Python CLI pipeline that cleans telemetry readings, summarizes device
temperatures from CSV, exports JSON, and plots average temperature by device.
Temperature readings are assumed to be in degrees Celsius (°C).

## Project structure

```text
device-log-summarizer/
├── .gitignore
├── README.md
├── PROMPT_LOG.md
├── requirements.txt
├── device_telemetry.csv
├── cleaning.py
├── test_cleaning.py
├── summarizer.py
├── test_summarizer.py
├── plot_temperatures.py
├── test_plot_temperatures.py
└── output/
    ├── summary.json
    └── temperature_chart.png
```

## Install

Use Python 3.10 or later:

```shell
python -m pip install -r requirements.txt
```

## Run

From this directory, summarize the sample CSV with the default threshold of
80.0 °C:

```shell
python summarizer.py
```

Specify input, output, or threshold as needed:

```shell
python summarizer.py --input device_telemetry.csv --output output/summary.json --threshold 80.0
```

Create a chart from the exported JSON:

```shell
python plot_temperatures.py
```

The chart accepts `--input` and `--output` paths. Both scripts create output
directories when needed.

## Tests

```shell
python -m pytest
```

## Example CLI output

```text
DEVICE_ID     RECORDS   AVG_TEMP   ERRORS
DEV_A               8      23.50        1
DEV_B               8      38.50        1
DEV_C               8      62.50        1
DEV_E               8      80.00        1
Rows read: 44 | Rows valid: 40 | Rows skipped: 4 | Devices removed by filter: 1
```

## JSON schema

The output contains the threshold used and a device list sorted by ID:

```json
{
  "threshold": 80.0,
  "devices": [
    {
      "device_id": "DEV_A",
      "total_records": 8,
      "avg_temperature": 23.5,
      "error_count": 1
    }
  ]
}
```

## Design decisions

- Invalid data rows are logged and skipped so one malformed reading does not
  stop processing the file. Status values are trimmed and compared
  case-insensitively.
- Devices are removed only when their average is strictly greater than the
  threshold; a device exactly at 80.0 remains when using the default.
- Devices are filtered using the exact mean; averages are rounded to two
  decimal places only for display and export.
- Sensor readings below zero and non-finite readings are invalid; readings
  above 500.0 are logged and capped at 500.0.
- The plotting script uses Matplotlib's non-interactive `Agg` backend and saves
  the PNG without opening a display.

## Limitations

- Readings above 500.0 are capped, logged, and kept in the summary.
- Rows with an unknown status are skipped.
