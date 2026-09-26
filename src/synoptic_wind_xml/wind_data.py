from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class StationMetadata:
    station_id: str
    name: str
    latitude: str
    longitude: str
    wind_sensor_height_meters: str | None


@dataclass(frozen=True)
class WindSeries:
    speeds: list[float]
    directions: list[float]
    timestamps: list[datetime]
