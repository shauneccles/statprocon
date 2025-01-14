# statprocon

**statprocon** is a Python helper library for generating data for use in **Stat**istical **Pro**cess **Con**trol charts.
SPC charts are also known as Process Behaviour Charts, Control charts or Shewhart charts.

SPC Charts help answer questions like:
- How do I know a change has occurred in a process?
- What is the expected variation in a process?
- Is a process stable or unpredictable?

## Installation

```shell
pip install statprocon
```
To install with the ability to draw plots, install with the plot extras:
```shell
pip install statprocon[plot]
```

## Usage

```python
from statprocon import XmR

counts = [10, 50, 40, 30]

xmr = XmR(counts)
moving_ranges = xmr.moving_ranges()
unpl = xmr.upper_natural_process_limit()[0]  # 85.7
lnpl = xmr.lower_natural_process_limit()[0]  # -20.7
x_cl = xmr.x_central_line()[0]  # 32.5

url = xmr.upper_range_limit()[0]  # 65.36
mr_cl = xmr.mr_central_line()[0]  # 20

```

Currently, this library only supports the data for generating an XmR chart.
An XmR chart is the most universal way of using process behaviour charts.
XmR is short for individual values (X) and a moving range (mR).
More chart data options can be added via pull requests.

For more information, please read [Making Sense of Data by Donald Wheeler](https://www.amazon.com/Making-Sense-Data-Donald-Wheeler/dp/0945320728).

### pandas

Visualize XmR charts using Jupyter Notebooks and [pandas](https://pandas.pydata.org/)

```python
import pandas as pd
from statprocon import XmR

xmr = XmR(counts)

pd.DataFrame(xmr.x_to_dict()).astype(float).plot()
pd.DataFrame(xmr.mr_to_dict()).astype(float).plot()
```

![Screenshot from 2023-07-22 13-53-22](https://github.com/mattmccormick/statprocon/assets/436801/b6a83903-4bb9-4935-9acb-c086d3420fd2)

Charts can display X-axis labels by using the following code:

```python
labels = ['0', '1', '2', '3']
pd.DataFrame(xmr.x_to_dict(), index=labels).astype(float).plot()
```

Or use built-in methods to generate charts that highlight detection points - you must have installed statprocon with the plot extra:

```python
import pandas as pd

labels = ['J', 'F', 'M', ...]
xmr = XmR(counts)
xmr.x_plot(pd, labels)
xmr.mr_plot(pd, labels)
```

![Screenshot from 2023-09-10 11-27-40](https://github.com/mattmccormick/statprocon/assets/436801/40fd200b-c22d-442a-8dc8-b97ef1fb0a12)

Data points that meet detection rules are marked by the following colours:

|Rule|Colour|
|---|---|
|Rule 1|Red|
|Rule 2|Green|
|Rule 3|Orange|

If one data point meets the criteria for multiple detection rules, the lower numbered detection rule will take priority and be marked.
For example, if a data point meets all detection rules, it will be displayed in red.
If a data point meets rule 2 and rule 3, it will be displayed in green.

### CSV

Generate a CSV of all the data needed to create XmR charts.

```python
print(xmr.to_csv())
```

### Google Sheets Charts

Generate XmR Charts in Google Sheets

https://github.com/mattmccormick/statprocon/assets/436801/0de1a9f3-a8ad-4047-8c9d-0f890e0bf453

1. Make a copy of the [statprocon XmR Template sheet](https://docs.google.com/spreadsheets/d/1IdCBpE8FK4qP8B7qHQeXX6amLZ8oyhc8OjlBlGHmWTg/edit?usp=sharing)
1. Paste the CSV output from above into cell A1
1. Click `Data -> Split Text to Columns`

The X and MR charts will appear on the right.

Note that the Lower Natural Process Limit may not make sense if your count data could not possibly go negative.
If LNPL is not needed, remove it with the following steps:

1. Double-click on the X Chart
1. Click the `Setup` tab
1. Under `Series`, find `LNPL`
1. Click the 3 dot menu on the right next to `LNPL`
1. Click `Remove`

The LNPL line will be removed from the X Chart.

## Advanced Usage

### Halfway Lines

Halfway lines between the X central line and the Upper and Lower Natural Process Limits can be returned by using the `include_halfway_lines` argument:

```python
xmr.x_to_dict(include_halfway_lines=True)
```

When the process is predictable, approximately 85% of the X values fall between the Upper and Lower halfway lines.

### Trending Limits

With data points that trend upwards or downwards over time, use Trending Limits to calculate a sloping X central line, Upper Natural Process Limits and Lower Natural Process Limits.

```python
from statprocon import XmRTrending

counts = [...]  # data from TrendingTestCase.test_trending_limits

source = XmR(counts)
trending = XmRTrending(source)
pd.DataFrame(trending.x_to_dict()).astype(float).plot()
```

![trending-limits](https://github.com/mattmccormick/statprocon/assets/436801/d0d9897e-b1b7-469b-9642-fbee8f39b104)


### Use the Median Moving Range

If your data contains extreme outliers, it may be better to compute the limits using the median moving range.

```python
xmr = XmR(counts, moving_range_uses='median')
```

### Use the Median for the X Central Line

```python
xmr = XmR(counts, x_central_line_uses='median')
```

Note: It's assumed that by using the median for the X central line that the median moving range should also be used.
For example, you **cannot** do the following:

```python
xmr = XmR(counts, x_central_line_uses='median', moving_range_uses='average')
```

### Calculate Limits from Subset of Counts

The central lines and limits calculations can be restricted to a subset of the count data.
Use the `subset_start_index` and `subset_end_index` parameters when instantiating the XmR object:

```python
xmr = XmR(counts, subset_start_index=10, subset_end_index=34)  # 24 points of data starting at index 10
```

When one or both of these optional arguments are provided, the the X and MR central line calculations will be modified to only use the data from `subset_start_index` up to, but not including, `subset_end_index`.
When these optional arguments are not provided, `subset_start_index` defaults to 0 and `subset_end_index` defaults to the length of `counts`.

## Dependencies

There are a few other Python libraries for generating SPC charts but they all contain large dependencies in order to include the ability to graph the chart.
This package will remain small and light and not require large dependencies.
The user will need to convert the data into charts on their own.

This package also contains extensive tests for verifying the integrity of the calculated data.

---
## Development

Create uv virtual environment

```shell
uv sync --all-extras --dev
```

[Build](https://docs.astral.sh/uv/concepts/projects/build/)

```shell
uv build
```

[Upload](https://docs.astral.sh/uv/guides/publish/)

```shell
uv publish
```

### Testing

[Install package from source](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#installing-from-source)
```shell
uv sync --all-extras --dev
```

Run tests
```shell
uv run python -m unittest discover
```

Run type checking
```shell
uv run mypy statprocon tests
```