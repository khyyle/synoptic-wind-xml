import logging
import os
from datetime import datetime

import requests

from synoptic_wind_xml.wind_data import StationMetadata, WindSeries

# api configuration
SYNOPTIC_TOKEN_ENV = "SYNOPTIC_TOKEN"
LATEST_STATIONS_URL = "https://api.synopticdata.com/v2/stations/latest"
TIMESERIES_URL = "https://api.synopticdata.com/v2/stations/timeseries"
SYNOPTIC_TIME_FORMAT = "%Y%m%d%H%M"

# synoptic API status
SYNOPTIC_OK = 1
SYNOPTIC_ZERO_RESULTS = 2
REQUEST_TIMEOUT_SECONDS = 30

# station lookup parameters
SEARCH_RADIUS_MILES = 25
# observation filtering
INCOMPLETE_OBSERVATION_WARNING_COUNT = 20

logger = logging.getLogger(__name__)


class SynopticRequestError(RuntimeError):
    """Synoptic rejected a request, or the request could not be sent."""


class NoStationsFoundError(LookupError):
    """A station search matched no stations."""


def load_synoptic_token() -> str:
    """
    Read the Synoptic API token from the environment.

    Returns
    -------
    str
        Token value from SYNOPTIC_TOKEN.

    Raises
    ------
    SynopticRequestError
        If SYNOPTIC_TOKEN is missing or empty.
    """
    token = os.environ.get(SYNOPTIC_TOKEN_ENV)
    if not token:
        raise SynopticRequestError(
            f"{SYNOPTIC_TOKEN_ENV} is not set. Add it to the environment or a .env file."
        )
    return token


def _get_stations(url: str, params: dict[str, str | int]) -> list[dict]:
    """
    Send a Synoptic request and return the stations it matched.

    Parameters
    ----------
    url: str
        Synoptic endpoint.
    params: dict[str, str | int]
        Query parameters, without the token.

    Returns
    -------
    list[dict]
        Station objects from the response. Empty when nothing matched.

    Raises
    ------
    SynopticRequestError
        If Synoptic cannot be reached, the HTTP status is not OK, or Synoptic
        reports an error response code.
    """
    try:
        response = requests.get(
            url,
            params={"token": load_synoptic_token(), **params},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        raise SynopticRequestError(f"Could not reach Synoptic: {error}") from error

    try:
        body = response.json()
        summary = body["SUMMARY"]
    except (ValueError, KeyError):
        raise SynopticRequestError(
            f"Synoptic returned HTTP {response.status_code} without a readable summary"
        ) from None

    if not response.ok or summary["RESPONSE_CODE"] not in (SYNOPTIC_OK, SYNOPTIC_ZERO_RESULTS):
        raise SynopticRequestError(
            f"Synoptic request failed (HTTP {response.status_code}): {summary['RESPONSE_MESSAGE']}"
        )

    if summary["RESPONSE_CODE"] == SYNOPTIC_ZERO_RESULTS:
        return []
    return body["STATION"]


def find_nearest_station_id(latitude: float, longitude: float) -> str:
    """
    Return the id of the closest station within SEARCH_RADIUS_MILES.

    Parameters
    ----------
    latitude: float
        Latitude of the point to search from, in degrees.
    longitude: float
        Longitude of the point to search from, in degrees.

    Returns
    -------
    str
        Synoptic station id of the closest station.

    Raises
    ------
    NoStationsFoundError
        If no station is inside the search radius.
    SynopticRequestError
        If Synoptic rejects the request.
    """
    stations = _get_stations(
        url=LATEST_STATIONS_URL,
        params={
            "radius": f"{latitude},{longitude},{SEARCH_RADIUS_MILES}",
            "limit": 1,
            "vars": "wind_speed,wind_direction",
        },
    )
    if not stations:
        raise NoStationsFoundError(f"No station within {SEARCH_RADIUS_MILES} miles was found.")
    return stations[0]["STID"]


def find_station_ids_in_rectangle(
    southwest_latitude: float,
    southwest_longitude: float,
    northeast_latitude: float,
    northeast_longitude: float,
) -> list[str]:
    """
    Return station ids inside a latitude-longitude rectangle.

    Parameters
    ----------
    southwest_latitude: float
        Latitude of the southwest corner, in degrees.
    southwest_longitude: float
        Longitude of the southwest corner, in degrees.
    northeast_latitude: float
        Latitude of the northeast corner, in degrees.
    northeast_longitude: float
        Longitude of the northeast corner, in degrees.

    Returns
    -------
    list[str]
        Station ids inside the rectangle.

    Raises
    ------
    NoStationsFoundError
        If the rectangle contains no stations.
    SynopticRequestError
        If Synoptic rejects the request.
    """
    stations = _get_stations(
        url=LATEST_STATIONS_URL,
        params={
            "bbox": (
                f"{southwest_longitude},{southwest_latitude},"
                f"{northeast_longitude},{northeast_latitude}"
            ),
        },
    )
    if not stations:
        raise NoStationsFoundError("No stations found within the specified area.")
    return [station["STID"] for station in stations]


def fetch_wind_observations(
    station_id: str, start: datetime, end: datetime
) -> tuple[StationMetadata, WindSeries] | None:
    """
    Download one station's wind observations, keeping only samples that have
    both a speed and a direction.

    Parameters
    ----------
    station_id: str
        Synoptic station id.
    start: datetime
        Range start, in UTC.
    end: datetime
        Range end, in UTC.

    Returns
    -------
    station_metadata: StationMetadata
        The station's id, name, location, and wind sensor height.
    observed: WindSeries
        Speed in m/s and direction in degrees clockwise from north (the
        direction the wind comes from), at UTC timestamps.

    None when the station reported no complete wind samples in the queried range.

    Raises
    ------
    SynopticRequestError
        If Synoptic rejects the request, for example a bad token or a range in
        the future.
    """
    stations = _get_stations(
        url=TIMESERIES_URL,
        params={
            "stid": station_id,
            "vars": "wind_speed,wind_direction",
            "start": start.strftime(SYNOPTIC_TIME_FORMAT),
            "end": end.strftime(SYNOPTIC_TIME_FORMAT),
            "qc_checks": "basic",
            "qc": "on",
            "sensorvars": 1,
        },
    )
    if not stations:
        logger.warning("%s: no wind observations between %s and %s, skipping", station_id, start, end)
        return None

    station = stations[0]
    observations = station["OBSERVATIONS"]
    if "wind_speed_set_1" not in observations or "wind_direction_set_1" not in observations:
        logger.warning("%s: reports wind speed or direction but not both, skipping", station_id)
        return None

    complete_samples = [
        (timestamp, speed, direction)
        for timestamp, speed, direction in zip(
            observations["date_time"],
            observations["wind_speed_set_1"],
            observations["wind_direction_set_1"],
            strict=True,
        )
        if speed is not None and direction is not None
    ]
    dropped_sample_count = len(observations["date_time"]) - len(complete_samples)
    if dropped_sample_count > INCOMPLETE_OBSERVATION_WARNING_COUNT:
        logger.warning(
            "%s: dropped %d samples missing speed or direction", station_id, dropped_sample_count
        )
    if not complete_samples:
        logger.warning(
            "%s: no samples with both speed and direction between %s and %s, skipping",
            station_id,
            start,
            end,
        )
        return None

    timestamps, wind_speeds, wind_directions = (
        list(values) for values in zip(*complete_samples, strict=True)
    )
    observed = WindSeries(
        speeds=wind_speeds,
        directions=wind_directions,
        timestamps=[datetime.fromisoformat(timestamp) for timestamp in timestamps],
    )
    metadata = StationMetadata(
        station_id=station["STID"],
        name=station["NAME"],
        latitude=station["LATITUDE"],
        longitude=station["LONGITUDE"],
        wind_sensor_height_meters=_wind_sensor_height_meters(station),
    )
    return metadata, observed


def _wind_sensor_height_meters(station: dict) -> str | None:
    wind_speed_sensor = (
        station.get("SENSOR_VARIABLES", {}).get("wind_speed", {}).get("wind_speed_set_1", {})
    )
    position = wind_speed_sensor.get("position")
    if position in (None, ""):
        return None
    return str(position)
