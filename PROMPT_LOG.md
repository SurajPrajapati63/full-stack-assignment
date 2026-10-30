# Prompt Log

## Initial prompt
I have a JSON file at output/summary.json like this:

{
  "threshold": 80.0,
  "devices": [
    {"device_id": "DEV_A", "total_records": 8, "avg_temperature": 23.5, "error_count": 1},
    {"device_id": "DEV_B", "total_records": 8, "avg_temperature": 38.5, "error_count": 1}
  ]
}

Write a Python script using matplotlib that reads this file and makes a bar
chart of the average temperature for each device. Save the chart as a PNG.

## Bug or mistake in the first attempt
<Replace with what you actually saw. Examples of real first-attempt problems:
- The chart had no title or axis labels.
- It used plt.show(), which does nothing when I run it without a display.
- It crashed with a traceback when summary.json was missing.
- Bars had no value labels, and the threshold from the JSON was ignored.>

## Follow-up prompt
<Replace with the exact message you sent. Example for the problem above:
"The chart works but it has no title or axis labels and I can't see the exact
values. Please add a title, label the x-axis 'Device' and the y-axis 'Average
Temperature (°C)', show the value on top of each bar, draw a dashed line at the
threshold from the JSON, and save the file instead of calling plt.show().">

Result: <One line: did it fix the problem? What did you still change by hand?>