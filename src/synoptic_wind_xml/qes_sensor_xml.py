import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from synoptic_wind_xml.wind_data import StationMetadata, WindSeries

QES_SITE_COORD_FLAG_LAT_LON = "3"
QES_LOG_PROFILE_FLAG = "1"
SURFACE_ROUGHNESS_METERS = "0.1"
NEUTRAL_RECIPROCAL_OBUKHOV_LENGTH = "0.0"
DEFAULT_SENSOR_HEIGHT_METERS = "10.0"
# QES reads timeStamp with Boost's ISO parser, which rejects a UTC offset or trailing "Z".
QES_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"

SPEED_DECIMAL_PLACES = 3
DIRECTION_DECIMAL_PLACES = 2

logger = logging.getLogger(__name__)


def write_wind_xml(station: StationMetadata, series: WindSeries, folder: Path) -> Path:
    """
    Write one station's wind series as a QES-Winds sensor XML file.

    Every time step uses a logarithmic profile with the same surface roughness and
    neutral stability. The height is the station's wind sensor height. When
    Synoptic lists none, the height is `DEFAULT_SENSOR_HEIGHT_METERS` and the file
    carries a comment saying so, because QES needs a real number in `height`.

    Parameters
    ----------
    station: StationMetadata
        Station whose id, name, location, and sensor height go in the file.
    series: WindSeries
        Speed, direction, and UTC timestamp for every time step.
    folder: Path
        Directory that receives <station id>.xml. Created if missing.

    Returns
    -------
    Path
        The file that was written.
    """
    root = ET.Element("sensor")
    root.append(ET.Comment(f"Station Name: {station.name}"))
    root.append(ET.Comment(f"Station ID: {station.station_id}"))

    sensor_height = station.wind_sensor_height_meters
    if sensor_height is None:
        sensor_height = DEFAULT_SENSOR_HEIGHT_METERS
        default_height_note = (
            f"Height defaulted to {DEFAULT_SENSOR_HEIGHT_METERS} m: "
            "Synoptic lists no wind sensor height for this station"
        )
        root.append(ET.Comment(default_height_note))
        logger.warning("%s: %s", station.station_id, default_height_note)

    ET.SubElement(root, "site_coord_flag").text = QES_SITE_COORD_FLAG_LAT_LON
    ET.SubElement(root, "site_lat").text = station.latitude
    ET.SubElement(root, "site_lon").text = station.longitude

    for timestamp, speed, direction in zip(
        series.timestamps, series.speeds, series.directions, strict=True
    ):
        time_series = ET.SubElement(root, "timeSeries")
        ET.SubElement(time_series, "timeStamp").text = timestamp.strftime(QES_TIMESTAMP_FORMAT)
        ET.SubElement(time_series, "boundaryLayerFlag").text = QES_LOG_PROFILE_FLAG
        ET.SubElement(time_series, "siteZ0").text = SURFACE_ROUGHNESS_METERS
        ET.SubElement(time_series, "reciprocal").text = NEUTRAL_RECIPROCAL_OBUKHOV_LENGTH
        ET.SubElement(time_series, "height").text = sensor_height
        ET.SubElement(time_series, "speed").text = str(round(speed, SPEED_DECIMAL_PLACES))
        ET.SubElement(time_series, "direction").text = str(
            round(direction, DIRECTION_DECIMAL_PLACES)
        )

    tree = ET.ElementTree(root)
    ET.indent(tree, "  ")
    folder.mkdir(parents=True, exist_ok=True)
    xml_path = folder / f"{station.station_id}.xml"
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    return xml_path
