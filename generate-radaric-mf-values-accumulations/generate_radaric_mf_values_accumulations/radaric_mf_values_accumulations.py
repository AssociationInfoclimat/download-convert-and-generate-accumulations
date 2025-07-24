import os
from pathlib import Path
from typing import Protocol

from .datetime_utils import (
    FIVE_MINUTES_IN_SECONDS,
    ONE_DAY_IN_SECONDS,
    ONE_HOUR_IN_SECONDS,
    ONE_MINUTE_IN_SECONDS,
)
from .tiles import (
    AccumulationDuration,
    PrecipitationsParam,
    Zone,
    get_tif_path_for_param_in_zone_at,
)


def get_range(
    start: int,
    end: int,
    step: int,
    *,
    exclude_start: bool = False,
    exclude_end: bool = True,
):
    if exclude_start:
        start += step
    if not exclude_end:
        end += step
    return range(start, end, step)


def get_accumulation_range(start: int, end: int, step: int):
    return get_range(
        start,
        end,
        step,
        exclude_start=True,
        exclude_end=False,
    )


def get_timestamps_for_cumul_1h_at(timestamp: int) -> list[int]:
    return list(
        get_accumulation_range(
            timestamp - ONE_HOUR_IN_SECONDS,
            timestamp,
            FIVE_MINUTES_IN_SECONDS,
        )
    )


def get_timestamps_for_interpolated_cumul_1h_at(timestamp: int) -> list[int]:
    return list(
        get_range(
            timestamp - ONE_HOUR_IN_SECONDS + FIVE_MINUTES_IN_SECONDS,
            timestamp,
            ONE_MINUTE_IN_SECONDS,
            exclude_start=False,
            exclude_end=False,
        )
    )


def get_tifs_pathes_to_read_for_cumul_1h_in_zone_at(zone: Zone, timestamp: int):
    timestamps_to_read = get_accumulation_range(
        timestamp - ONE_HOUR_IN_SECONDS,
        timestamp,
        FIVE_MINUTES_IN_SECONDS,
    )
    return (
        get_tif_path_for_param_in_zone_at(PrecipitationsParam.VALUES_5MN, zone, t)
        for t in timestamps_to_read
    )


def get_tifs_pathes_to_read_for_cumul_3h_in_zone_at(zone: Zone, timestamp: int):
    timestamps_to_read = get_accumulation_range(
        timestamp - 3 * ONE_HOUR_IN_SECONDS,
        timestamp,
        ONE_HOUR_IN_SECONDS,
    )
    return (
        get_tif_path_for_param_in_zone_at(PrecipitationsParam.VALUES_1H, zone, t)
        for t in timestamps_to_read
    )


def get_tifs_pathes_to_read_for_cumul_6h_in_zone_at(zone: Zone, timestamp: int):
    timestamps_to_read = get_accumulation_range(
        timestamp - 6 * ONE_HOUR_IN_SECONDS,
        timestamp,
        ONE_HOUR_IN_SECONDS,
    )
    return (
        get_tif_path_for_param_in_zone_at(PrecipitationsParam.VALUES_1H, zone, t)
        for t in timestamps_to_read
    )


def get_tifs_pathes_to_read_for_cumul_12h_in_zone_at(zone: Zone, timestamp: int):
    timestamps_to_read = get_accumulation_range(
        timestamp - 12 * ONE_HOUR_IN_SECONDS,
        timestamp,
        ONE_HOUR_IN_SECONDS,
    )
    return (
        get_tif_path_for_param_in_zone_at(PrecipitationsParam.VALUES_1H, zone, t)
        for t in timestamps_to_read
    )


def get_tifs_pathes_to_read_for_cumul_24h_in_zone_at(zone: Zone, timestamp: int):
    timestamps_to_read = get_accumulation_range(
        timestamp - ONE_DAY_IN_SECONDS,
        timestamp,
        ONE_HOUR_IN_SECONDS,
    )
    return (
        get_tif_path_for_param_in_zone_at(PrecipitationsParam.VALUES_1H, zone, t)
        for t in timestamps_to_read
    )


def get_tifs_pathes_to_read_for_cumul_72h_in_zone_at(zone: Zone, timestamp: int):
    timestamps_to_read = get_accumulation_range(
        timestamp - 3 * ONE_DAY_IN_SECONDS,
        timestamp,
        ONE_DAY_IN_SECONDS,
    )
    return (
        get_tif_path_for_param_in_zone_at(PrecipitationsParam.VALUES_24H, zone, t)
        for t in timestamps_to_read
    )


def get_tifs_pathes_to_read_for_cumul_in_zone_at(
    zone: Zone, timestamp: int, accumulation_duration: AccumulationDuration
):
    if accumulation_duration == AccumulationDuration.CUMUL_1H:
        return get_tifs_pathes_to_read_for_cumul_1h_in_zone_at(zone, timestamp)
    if accumulation_duration == AccumulationDuration.CUMUL_3H:
        return get_tifs_pathes_to_read_for_cumul_3h_in_zone_at(zone, timestamp)
    if accumulation_duration == AccumulationDuration.CUMUL_6H:
        return get_tifs_pathes_to_read_for_cumul_6h_in_zone_at(zone, timestamp)
    if accumulation_duration == AccumulationDuration.CUMUL_12H:
        return get_tifs_pathes_to_read_for_cumul_12h_in_zone_at(zone, timestamp)
    if accumulation_duration == AccumulationDuration.CUMUL_24H:
        return get_tifs_pathes_to_read_for_cumul_24h_in_zone_at(zone, timestamp)
    if accumulation_duration == AccumulationDuration.CUMUL_72H:
        return get_tifs_pathes_to_read_for_cumul_72h_in_zone_at(zone, timestamp)
    raise ValueError(f"Unknown accumulation duration: {accumulation_duration}")


def get_palette_file_path_for(palette_name: str) -> str:
    return str((Path(__file__).parent.parent.parent / "palettes" / f"{palette_name}.cpt").resolve())


def get_radar_palette_file_path_for(accumulation_duration: AccumulationDuration) -> str:
    return get_palette_file_path_for(f"radar{accumulation_duration.value}")


def get_generate_color_tif_from_values_command(
    values_tif_path: str, color_tif_path: str, palette_path: str
) -> str:
    return f"gdaldem color-relief {values_tif_path} {palette_path} {color_tif_path} -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'"


class CommandExecutor(Protocol):
    def execute(self, command: str) -> None: ...


class RealCommandExecutor(CommandExecutor):
    def execute(self, command: str) -> None:
        os.system(command)


class InMemoryCommandExecutor(CommandExecutor):
    def __init__(self) -> None:
        self.commands: list[str] = []

    def execute(self, command: str) -> None:
        self.commands.append(command)


def generate_color_tif_from_values(
    values_tif_path: str,
    color_tif_path: str,
    accumulation_duration: AccumulationDuration,
    *,
    command_executor: CommandExecutor,
) -> None:
    palette_path = get_radar_palette_file_path_for(accumulation_duration)
    command_executor.execute(
        get_generate_color_tif_from_values_command(values_tif_path, color_tif_path, palette_path)
    )
