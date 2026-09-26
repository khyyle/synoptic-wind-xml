import logging
from datetime import datetime
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from synoptic_wind_xml import prompts, synoptic_wind
from synoptic_wind_xml.plots import save_wind_plots
from synoptic_wind_xml.prompts import ResampleSettings
from synoptic_wind_xml.qes_sensor_xml import write_wind_xml
from synoptic_wind_xml.resample import resample_wind

FOLDER_TIME_FORMAT = "%Y-%m-%d_%H%M"

logger = logging.getLogger(__name__)


def _export_directory(
    parent: Path,
    start: datetime,
    end: datetime,
    resample_settings: ResampleSettings | None,
) -> Path:
    folder_name = f"{start:{FOLDER_TIME_FORMAT}}_to_{end:{FOLDER_TIME_FORMAT}}"
    if resample_settings is not None:
        minutes = resample_settings.interval_minutes
        minutes_label = int(minutes) if minutes == int(minutes) else minutes
        method = "averaged" if resample_settings.use_time_averaging else "interpolated"
        folder_name = f"{folder_name}_{minutes_label}min_{method}"
    directory = parent / folder_name
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _export() -> None:
    station_ids = prompts.ask_station_ids()
    start, end = prompts.ask_time_range()
    resample_settings = prompts.ask_resample_settings()
    export_directory = _export_directory(prompts.ask_export_folder(), start, end, resample_settings)
    logger.info("Saving run to %s", export_directory)

    for station_id in station_ids:
        logger.info("Exporting %s", station_id)
        fetched = synoptic_wind.fetch_wind_observations(station_id, start, end)
        if fetched is None:
            continue
        station, observed = fetched

        resampled = None
        if resample_settings is not None:
            resampled = resample_wind(
                observed=observed,
                interval_minutes=resample_settings.interval_minutes,
                start=start,
                end=end,
                use_time_averaging=resample_settings.use_time_averaging,
            )

        save_wind_plots(station_id, observed, resampled, folder=export_directory)
        exported = resampled if resampled is not None else observed
        xml_path = write_wind_xml(station, exported, folder=export_directory)
        logger.info("Wrote %s", xml_path)


def main() -> None:
    logging.basicConfig(format="%(levelname)s: %(message)s")
    logging.getLogger(__package__).setLevel(logging.INFO)
    load_dotenv(find_dotenv(usecwd=True))
    try:
        synoptic_wind.load_synoptic_token()
        _export()
    except (synoptic_wind.SynopticRequestError, synoptic_wind.NoStationsFoundError) as error:
        logger.error("%s", error)
        raise SystemExit(1) from None
