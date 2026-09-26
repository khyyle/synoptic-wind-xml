import logging
from datetime import UTC, datetime, timedelta
from itertools import pairwise

import numpy as np

from synoptic_wind_xml.wind_data import WindSeries

SECONDS_PER_MINUTE = 60
LARGE_GAP_INTERVALS = 5

logger = logging.getLogger(__name__)


def resample_wind(
    observed: WindSeries,
    interval_minutes: float,
    start: datetime,
    end: datetime,
    use_time_averaging: bool,
) -> WindSeries:
    """
    Resample speed and direction onto every step of a requested interval via

    Parameters
    ----------
    observed: WindSeries
        The station's observations.
    interval_minutes: float
        Output spacing in minutes.
    start: datetime
        First output time, in UTC.
    end: datetime
        Latest allowed output time, in UTC.
    use_time_averaging: bool
        When true, each output value is the average of the samples in the step
        ending at that time. When false, each output value is a linear blend of
        the readings on either side.

    Returns
    -------
    WindSeries
        Speed, direction, and UTC timestamp at each step of the interval.
    """
    _warn_about_large_gaps(observed.timestamps, interval_minutes)

    observation_times = np.array([timestamp.timestamp() for timestamp in observed.timestamps])
    observed_speeds = np.array(observed.speeds)
    observed_eastward, observed_northward = _wind_to_components(
        np.array(observed.directions), observed_speeds
    )
    observed_wind = np.column_stack([observed_speeds, observed_eastward, observed_northward])
    output_times = _output_times(
        start.timestamp(), end.timestamp(), interval_minutes * SECONDS_PER_MINUTE
    )

    if use_time_averaging:
        resampled_wind = _time_average(observation_times, observed_wind, output_times)
    else:
        resampled_wind = _interpolate_wind(observation_times, observed_wind, output_times)

    speeds, eastward, northward = resampled_wind.T
    return WindSeries(
        speeds=speeds.tolist(),
        directions=_components_to_direction(eastward, northward).tolist(),
        timestamps=[datetime.fromtimestamp(epoch_seconds, UTC) for epoch_seconds in output_times],
    )


def _output_times(start_seconds: float, end_seconds: float, interval_seconds: float) -> np.ndarray:
    step_count = int((end_seconds - start_seconds) // interval_seconds) + 1
    return start_seconds + interval_seconds * np.arange(step_count)


def _warn_about_large_gaps(timestamps: list[datetime], interval_minutes: float) -> None:
    gap_limit = timedelta(minutes=interval_minutes * LARGE_GAP_INTERVALS)
    for earlier, later in pairwise(timestamps):
        if later - earlier > gap_limit:
            logger.warning(
                "no readings between %s and %s. This %s gap will be filled by interpolation...",
                earlier,
                later,
                later - earlier,
            )


def _interpolate_wind(
    observation_times: np.ndarray,
    observed_wind: np.ndarray,
    output_times: np.ndarray,
) -> np.ndarray:
    """
    Estimate speed and direction at each output time linearly from the
    readings on either side. 
    
    `output_times` before the first reading or after the last reading take on 
    that reading's values to avoid extrapolating.

    Suppose the output time is a fraction `alpha` from reading `i` to reading
    `j`. This function computes speed as:
        `s(alpha) = (1 - alpha) s_i + alpha s_j`

    And direction as:
        `u(alpha) = (1 - alpha) u_i + alpha u_j`
        `v(alpha) = (1 - alpha) v_i + alpha v_j`

    where `u` and `v` are the component wise magnitudes of the original wind vector:
        `u = -s * sin(theta),    v = -s * cos(theta)`

    The direction is rebuilt from the interpolated components, wrapped to [0, 360).
    Output times before the first reading or after the last take that reading's
    values, and an output time that matches a reading returns the reading itself.

    Parameters
    ----------
    observation_times: np.ndarray
        Observation times as Unix seconds, in increasing order.
    observed_wind: np.ndarray
        One row per reading: speed, eastward component, northward component.
    output_times: np.ndarray
        Times to evaluate, as Unix seconds.

    Returns
    -------
    np.ndarray
        One row per output time: speed, eastward component, northward component.
    """
    return np.column_stack([
        np.interp(output_times, observation_times, column) for column in observed_wind.T
    ])


def _time_average(
    observation_times: np.ndarray,
    observed_wind: np.ndarray,
    output_times: np.ndarray,
) -> np.ndarray:
    """
    Average speed and direction over the step ending at each output time. This function
    uses linear interpolation to recover observation times at each of the requested
    `output_times`.
    
    Suppose a step holds `n` samples. This function computes speed as:
        `s_bar = (s_1 + ... + s_n) / n`

    And direction from the mean components:
        `u_bar = (u_1 + ... + u_n) / n`
        `v_bar = (v_1 + ... + v_n) / n`

    where `u` and `v` are the components of each vector sample. The direction is 
    rebuilt from the mean components, wrapped to [0, 360).

    NOTE: The first output time has no earlier step, so its value is the sample
    at that time rather than an average.

    Parameters
    ----------
    observation_times: np.ndarray
        Observation times as Unix seconds, in increasing order.
    observed_wind: np.ndarray
        One row per reading: speed, eastward component, northward component.
    output_times: np.ndarray
        Regular output times as Unix seconds.

    Returns
    -------
    np.ndarray
        One row per output time: mean speed, mean eastward component, mean
        northward component.
    """
    sample_times = np.union1d(observation_times, output_times)
    samples = _interpolate_wind(observation_times, observed_wind, sample_times)
    step_starts = np.concatenate([output_times[:1], output_times[:-1]])
    return np.array([
        samples[(sample_times >= step_start) & (sample_times <= step_end)].mean(axis=0)
        for step_start, step_end in zip(step_starts, output_times, strict=True)
    ])


def _wind_to_components(
    directions_degrees: np.ndarray, speeds: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert wind directions and speeds into eastward and northward components:

    `u = -s sin(theta),  v = -s cos(theta)` where `theta` is the direction
    the wind comes from in degrees clockwise from north and `s` is the speed.

    Parameters
    ----------
    directions_degrees: np.ndarray
        Direction the wind comes from, in degrees clockwise from north.
    speeds: np.ndarray
        Wind speed in the same units as the observations.

    Returns
    -------
    eastward: np.ndarray
        Component toward the east.
    northward: np.ndarray
        Component toward the north.
    """
    directions_radians = np.radians(directions_degrees)
    return -speeds * np.sin(directions_radians), -speeds * np.cos(directions_radians)


def _components_to_direction(eastward: np.ndarray, northward: np.ndarray) -> np.ndarray:
    """
    Convert eastward and northward components to wind directions in degrees.

    Parameters
    ----------
    eastward: np.ndarray
        Component toward the east.
    northward: np.ndarray
        Component toward the north.

    Returns
    -------
    np.ndarray
        Direction the wind comes from, in degrees from 0 to 360.
    """
    return np.degrees(np.arctan2(-eastward, -northward)) % 360
