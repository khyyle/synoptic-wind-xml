import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pyproj
import questionary

from synoptic_wind_xml import synoptic_wind

USER_TIME_FORMAT = "%Y-%m-%d %H:%M"
UTM_LATITUDE_BAND_LETTERS = "CDEFGHJKLMNPQRSTUVWXYZ"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResampleSettings:
    interval_minutes: float
    use_time_averaging: bool


def _parse_utc_time(text: str) -> datetime:
    return datetime.strptime(text.strip(), USER_TIME_FORMAT).replace(tzinfo=UTC)


def _parse_utm(text: str) -> tuple[int, float, float]:
    zone, easting, northing = text.upper().split()
    return (
        int(zone.rstrip(UTM_LATITUDE_BAND_LETTERS)),
        float(easting.rstrip("E")),
        float(northing.rstrip("N")),
    )


def _valid_utc_time(text: str) -> bool | str:
    try:
        _parse_utc_time(text)
    except ValueError:
        return "Use YYYY-MM-DD HH:MM in UTC, for example 2023-08-17 18:00"
    return True


def _valid_utm(text: str) -> bool | str:
    try:
        _parse_utm(text)
    except ValueError:
        return "Use <zone> <easting> <northing>, for example 12T 425000 4512000"
    return True


def _valid_positive_number(text: str) -> bool | str:
    try:
        value = float(text)
    except ValueError:
        return "Enter a number"
    if value <= 0:
        return "Enter a number greater than 0"
    return True


def _valid_optional_positive_number(text: str) -> bool | str:
    if not text.strip():
        return True
    return _valid_positive_number(text)


def _valid_latitude_longitude(text: str) -> bool | str:
    parts = text.split()
    if len(parts) != 2:
        return "Enter latitude and longitude separated by a space"
    try:
        float(parts[0])
        float(parts[1])
    except ValueError:
        return "Latitude and longitude have to be numbers"
    return True


def _valid_station_ids(text: str) -> bool | str:
    if not text.split():
        return "Enter at least one station id"
    return True


def _utm_to_latitude_longitude(zone: int, easting: float, northing: float) -> tuple[float, float]:
    utm_projection = pyproj.Proj(proj="utm", zone=zone, ellps="WGS84")
    longitude, latitude = utm_projection(easting, northing, inverse=True)
    return latitude, longitude


def _ask_utc_time(message: str, validate: Callable[[str], bool | str]) -> datetime:
    return _parse_utc_time(
        questionary.text(
            message,
            instruction="(UTC) YYYY-MM-DD HH:MM",
            validate=validate,
        ).unsafe_ask()
    )


def _ask_utm(message: str) -> tuple[int, float, float]:
    return _parse_utm(
        questionary.text(
            message,
            instruction="<zone> <easting> <northing>",
            validate=_valid_utm,
        ).unsafe_ask()
    )


def _ask_positive_meters(message: str) -> float:
    return float(questionary.text(message, validate=_valid_positive_number).unsafe_ask())


def _ask_nearest_to_latitude_longitude() -> list[str]:
    latitude_longitude = questionary.text(
        "Latitude and longitude",
        instruction="<latitude> <longitude>",
        validate=_valid_latitude_longitude,
    ).unsafe_ask()
    latitude, longitude = (float(part) for part in latitude_longitude.split())
    return [synoptic_wind.find_nearest_station_id(latitude, longitude)]


def _ask_nearest_to_utm() -> list[str]:
    latitude, longitude = _utm_to_latitude_longitude(*_ask_utm("UTM coordinates"))
    return [synoptic_wind.find_nearest_station_id(latitude, longitude)]


def _ask_station_id_list() -> list[str]:
    return questionary.text(
        "Station ids",
        instruction="<stid1> <stid2> ...",
        validate=_valid_station_ids,
    ).unsafe_ask().split()


def _ask_stations_in_area() -> list[str]:
    zone, easting, northing = _ask_utm("UTM coordinates of the southwest corner")
    east_distance_meters = _ask_positive_meters("Distance east of the corner, in meters")
    north_distance_meters = _ask_positive_meters("Distance north of the corner, in meters")
    southwest_latitude, southwest_longitude = _utm_to_latitude_longitude(zone, easting, northing)
    northeast_latitude, northeast_longitude = _utm_to_latitude_longitude(
        zone, easting + east_distance_meters, northing + north_distance_meters
    )
    logger.info(
        "Searching between southwest corner (%.5f, %.5f) and northeast corner (%.5f, %.5f)",
        southwest_latitude,
        southwest_longitude,
        northeast_latitude,
        northeast_longitude,
    )
    return synoptic_wind.find_station_ids_in_rectangle(
        southwest_latitude,
        southwest_longitude,
        northeast_latitude,
        northeast_longitude,
    )


def ask_station_ids() -> list[str]:
    """
    Ask how to choose stations and return their ids.

    Returns
    -------
    list[str]
        One station id for a coordinate search, or every id entered or found in an area.

    Raises
    ------
    NoStationsFoundError
        If a coordinate search or area finds no station.
    SynopticRequestError
        If Synoptic rejects a station search.
    """
    ask_for_stations = questionary.select(
        "How do you want to choose stations?",
        choices=[
            questionary.Choice(
                "Nearest to a latitude and longitude", value=_ask_nearest_to_latitude_longitude
            ),
            questionary.Choice("Nearest to UTM coordinates", value=_ask_nearest_to_utm),
            questionary.Choice("Station ids", value=_ask_station_id_list),
            questionary.Choice("Rectangular area (UTM corner + size)", value=_ask_stations_in_area),
        ],
    ).unsafe_ask()
    return ask_for_stations()


def ask_time_range() -> tuple[datetime, datetime]:
    """
    Ask for the start and end of the export.

    Returns
    -------
    start: datetime
        Start, in UTC.
    end: datetime
        End, in UTC. Always after the start.
    """
    start = _ask_utc_time("Start time", _valid_utc_time)

    def valid_end_time(text: str) -> bool | str:
        time_check = _valid_utc_time(text)
        if time_check is not True:
            return time_check
        if _parse_utc_time(text) <= start:
            return "End time has to be after the start time"
        return True

    return start, _ask_utc_time("End time", valid_end_time)


def ask_resample_settings() -> ResampleSettings | None:
    """
    Ask for a shared time step for every station, and how to fill it.

    Returns
    -------
    ResampleSettings | None
        The step length and method, or None to keep each station's own
        report times.
    """
    interval_text = questionary.text(
        "Minutes per step",
        instruction="leave blank to export only station report times",
        validate=_valid_optional_positive_number,
    ).unsafe_ask()
    if not interval_text.strip():
        return None
    interval_minutes = float(interval_text)
    use_time_averaging = questionary.select(
        "Value at each step",
        choices=[
            questionary.Choice(
                "Linear interpolation",
                value=False,
                description="Blend linearly from nearest readings",
            ),
            questionary.Choice(
                "Time average",
                value=True,
                description="Mean of the readings since the previous step",
            ),
        ],
    ).unsafe_ask()
    return ResampleSettings(interval_minutes, use_time_averaging)


def ask_export_folder() -> Path:
    """
    Ask for the folder that receives this export.

    Returns
    -------
    Path
        Folder path as typed
    """
    folder = questionary.path(
        "Folder for this export",
        only_directories=True,
    ).unsafe_ask()
    return Path(folder).expanduser()
