from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from synoptic_wind_xml.wind_data import WindSeries


def _save_series_plot(
    observed_timestamps: list[datetime],
    observed_values: list[float],
    resampled_timestamps: list[datetime] | None,
    resampled_values: list[float] | None,
    linestyle: str,
    ylabel: str,
    title: str,
    output_path: Path,
) -> None:
    figure, axes = plt.subplots()
    axes.plot(
        observed_timestamps,
        observed_values,
        label="observations",
        marker="o",
        linestyle=linestyle,
    )
    if resampled_timestamps is not None:
        axes.plot(
            resampled_timestamps,
            resampled_values,
            label="resampled",
            marker="x",
            linestyle=linestyle,
        )
    axes.set_xlabel("time (UTC)")
    axes.set_ylabel(ylabel)
    axes.set_title(title)
    axes.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
    axes.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(axes.get_xticklabels(), rotation=17)
    axes.grid(True)
    axes.legend()
    figure.savefig(output_path)
    plt.close(figure)


def save_wind_plots(
    station_id: str,
    observed: WindSeries,
    resampled: WindSeries | None,
    folder: Path,
) -> None:
    """
    Save a speed plot and a direction plot for one station.

    Parameters
    ----------
    station_id: str
        Station id, used in the titles and file names.
    observed: WindSeries
        The station's observations.
    resampled: WindSeries | None
        The resampled series to draw over the observations, or None for a run
        that keeps the station's own report times.
    folder: Path
        Directory that receives <station id>_speed.png and <station id>_direction.png.
    """
    _save_series_plot(
        observed.timestamps,
        observed.speeds,
        resampled.timestamps if resampled else None,
        resampled.speeds if resampled else None,
        "-",
        "Wind speed (m/s)",
        f"{station_id} wind speed",
        folder / f"{station_id}_speed.png",
    )
    _save_series_plot(
        observed.timestamps,
        observed.directions,
        resampled.timestamps if resampled else None,
        resampled.directions if resampled else None,
        "none", # use unconnected markers for direction to avoid 0-360 weirdness
        "Wind direction (degrees)",
        f"{station_id} wind direction",
        folder / f"{station_id}_direction.png",
    )
