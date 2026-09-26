# synoptic-wind-xml

A CLI tool that downloads wind observations from the [Synoptic time series API](https://docs.synopticdata.com/services/time-series) and writes one [QES-Winds](https://qes-documentation.readthedocs.io/en/latest/QES-Winds.html) sensor XML file per station.

## Features

- Pick stations by the nearest to a latitude/longitude or UTM point, station id, or by a UTM rectangle.
- Keep each station's own report times, or put every station on the same fixed interval via linear interpolation, optionally averaging over each interval.
- Plots each station's speed and direction, with the resampled series drawn over the observations when resampling.

## Setup

Install the pinned Python 3.11 environment with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Create a free Synoptic account and copy a token from the Data Credentials tab at [customer.synopticdata.com](https://customer.synopticdata.com/). Copy `.env.example` to `.env` at the repository root and fill it in, or export it as an environment variable:

```text
SYNOPTIC_TOKEN=your-token
```

## Usage

From the repository root:

```bash
uv run synoptic-wind-xml
```

The script will ask how to pick stations, the start and end time in UTC, the minutes per output step (leave blank to keep each station's report times), and where to save. Each run is placed in a folder named after the queried time range and, for a resampled run, the interval and method:

```text
<save_directory>/
└── <start>_to_<end>[_<minutes>min_<interpolated|averaged>]/
    ├── <station_id>.xml
    ├── <station_id>_speed.png
    └── <station_id>_direction.png
```

The resulting XML exports have format:

```xml
<sensor>
  <!--Station Name: U of U William Browning Building-->
  <!--Station ID: WBB-->
  <site_coord_flag>3</site_coord_flag>
  <site_lat>40.76623</site_lat>
  <site_lon>-111.84755</site_lon>
  <timeSeries>
    <timeStamp>2026-09-24T12:00:00</timeStamp>
    <boundaryLayerFlag>1</boundaryLayerFlag>
    <siteZ0>0.1</siteZ0>
    <reciprocal>0.0</reciprocal>
    <height>42.0</height>
    <speed>1.008</speed>
    <direction>204.1</direction>
  </timeSeries>
  ...
</sensor>
```

Normally, Synoptic provides sensor `height`; when missing, the export defaults to `DEFAULT_SENSOR_HEIGHT_METERS = 10.0` and will show a comment under the Station ID:
```xml
<!--Height defaulted to 10.0 m: Synoptic lists no wind sensor height for this station-->
```

Otherwise, every time step is exported with the same wind profile: logarithmic (`boundaryLayerFlag` 1), 0.1 m surface roughness (`siteZ0`), and neutral stability (`reciprocal` 0). 
