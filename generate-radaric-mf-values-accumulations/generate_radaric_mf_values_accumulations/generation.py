import os
import time
from typing import Any, Iterable, Optional, Protocol

import numpy
from .arguments import Arguments
from osgeo import gdal
from scipy import integrate, interpolate

from .datetime_utils import (
    FIVE_MINUTES_IN_SECONDS,
    ONE_HOUR_IN_SECONDS,
    datetime_of,
    get_datetime_from_timestamp,
    timestamp_to_iso,
)
from .radaric_mf_values_accumulations import (
    CommandExecutor,
    RealCommandExecutor,
    generate_color_tif_from_values,
    get_tifs_pathes_to_read_for_cumul_in_zone_at,
    get_timestamps_for_cumul_1h_at,
    get_timestamps_for_interpolated_cumul_1h_at,
)
from .sql import get_sql_connection
from .tiles import (
    AccumulationDuration,
    PrecipitationsParam,
    RealTilesDatetimesRepository,
    TilesDatetimesRepository,
    Zone,
    get_param_key_for_zone,
    get_tif_path_for_param_in_zone_at,
    update_tile_last_timestamp,
)


class FileExistenceChecker(Protocol):
    def exists(self, path: str) -> bool: ...


class RealFileExistenceChecker(FileExistenceChecker):
    def exists(self, path: str) -> bool:
        return os.path.isfile(path)


class InMemoryFileExistenceChecker(FileExistenceChecker):
    def __init__(self, existing_files: Optional[set[str]] = None) -> None:
        self.existing_files: set[str] = existing_files or set()

    def exists(self, path: str) -> bool:
        return path in self.existing_files


def get_ram_path_for_param_in_zone_at(
    param: PrecipitationsParam,
    zone: Zone,
    timestamp: int,
) -> str:
    param_key = get_param_key_for_zone(param, zone)
    dt = get_datetime_from_timestamp(timestamp)
    return f"/dev/shm/{param_key}_{dt:%Y_%m_%d_%H_%M}.tif"


def move_from_ram_to_disk(
    ram_path: str,
    disk_path: str,
    *,
    command_executor: CommandExecutor,
) -> None:
    print(
        f"""
Move from RAM to disk :
  - RAM  : {ram_path}
  - Disk : {disk_path}
"""
    )
    command_executor.execute(f"mv {ram_path} {disk_path}")


def move_param_in_zone_at_from_ram_to_disk(
    param: PrecipitationsParam,
    zone: Zone,
    timestamp: int,
    *,
    command_executor: CommandExecutor,
) -> None:
    ram_path = get_ram_path_for_param_in_zone_at(param, zone, timestamp)
    disk_path = get_tif_path_for_param_in_zone_at(param, zone, timestamp)
    move_from_ram_to_disk(
        ram_path,
        disk_path,
        command_executor=command_executor,
    )


def copy_from_disk_to_ram(
    disk_path: str,
    ram_path: str,
    *,
    command_executor: CommandExecutor,
) -> None:
    print(
        f"""
Copy from disk to RAM :
  - Disk : {disk_path}
  - RAM  : {ram_path}
"""
    )
    command_executor.execute(f"cp {disk_path} {ram_path}")


def copy_param_in_zone_at_from_disk_to_ram(
    param: PrecipitationsParam,
    zone: Zone,
    timestamp: int,
    *,
    command_executor: CommandExecutor,
) -> None:
    disk_path = get_tif_path_for_param_in_zone_at(param, zone, timestamp)
    ram_path = get_ram_path_for_param_in_zone_at(param, zone, timestamp)
    copy_from_disk_to_ram(
        disk_path,
        ram_path,
        command_executor=command_executor,
    )


class TifConfig:
    def __init__(
        self,
        cols: int,
        rows: int,
        geo_transform: tuple[float, float, float, float, float, float],
        projection: str,
    ):
        self.cols = cols
        self.rows = rows
        self.geo_transform = geo_transform
        self.projection = projection


def read_tif(tif_path: str) -> Optional[gdal.Dataset]:
    try:
        return gdal.Open(tif_path, gdal.GA_ReadOnly)
    except:
        return None


class Transform(Protocol):
    def transform(
        self, array: Optional[numpy.ndarray[Any, Any]]
    ) -> Optional[numpy.ndarray[Any, Any]]: ...


class IdentityTransform(Transform):
    def transform(
        self, array: Optional[numpy.ndarray[Any, Any]]
    ) -> Optional[numpy.ndarray[Any, Any]]:
        return array


class MeteoFranceTransform(Transform):
    METEOFRANCE_NO_DATA_VALUE = 65535

    def transform(
        self, array: Optional[numpy.ndarray[Any, Any]]
    ) -> Optional[numpy.ndarray[Any, Any]]:
        if array is None:
            return None
        array[array == self.METEOFRANCE_NO_DATA_VALUE] = 0
        return array / 100


class TifReader(Protocol):
    def read_tif(
        self,
        tif_path: str,
        *,
        transform: Transform = IdentityTransform(),
    ) -> Optional[numpy.ndarray[Any, Any]]: ...


class RealTifReader(TifReader):
    def read_tif(
        self,
        tif_path: str,
        *,
        transform: Transform = IdentityTransform(),
    ) -> Optional[numpy.ndarray[Any, Any]]:
        dataset = read_tif(tif_path)
        return transform.transform(dataset.ReadAsArray() if dataset else None)


class InMemoryTifReader(TifReader):
    def __init__(
        self,
        tifs: Optional[dict[str, numpy.ndarray[Any, Any]]] = None,
    ) -> None:
        self.tifs: dict[str, numpy.ndarray[Any, Any]] = tifs or {}

    def read_tif(
        self,
        tif_path: str,
        *,
        transform: Transform = IdentityTransform(),
    ) -> Optional[numpy.ndarray[Any, Any]]:
        return transform.transform(self.tifs.get(tif_path, None))

    @staticmethod
    def from_list(tifs: dict[str, list[Any]]) -> "InMemoryTifReader":
        return InMemoryTifReader(
            {tif_path: numpy.array(array) for tif_path, array in tifs.items()}
        )


class SameInMemoryTifReader(TifReader):
    def __init__(
        self,
        array: Optional[numpy.ndarray[Any, Any]] = None,
    ) -> None:
        self.array: Optional[numpy.ndarray[Any, Any]] = array

    def read_tif(
        self,
        tif_path: str,
        *,
        transform: Transform = IdentityTransform(),
    ) -> Optional[numpy.ndarray[Any, Any]]:
        return transform.transform(self.array)

    @staticmethod
    def from_list(array: list[Any]) -> "SameInMemoryTifReader":
        return SameInMemoryTifReader(numpy.array(array))


class GDALOpenException(Exception):
    pass


def get_tif_config(timestamp: int, zone: Zone) -> Optional[TifConfig]:
    radaric_tif_path = get_tif_path_for_param_in_zone_at(
        PrecipitationsParam.VALUES_5MN, zone, timestamp
    )
    radaric_dataset = read_tif(radaric_tif_path)
    if not radaric_dataset:
        return None
    return TifConfig(
        cols=radaric_dataset.RasterXSize,
        rows=radaric_dataset.RasterYSize,
        geo_transform=radaric_dataset.GetGeoTransform(),
        projection=radaric_dataset.GetProjection(),
    )


class TifConfigGetter(Protocol):
    def get_tif_config(self, timestamp: int, zone: Zone) -> Optional[TifConfig]: ...


class RealTifConfigGetter(TifConfigGetter):
    def get_tif_config(self, timestamp: int, zone: Zone) -> Optional[TifConfig]:
        return get_tif_config(timestamp, zone)


class InMemoryTifConfigGetter(TifConfigGetter):
    def __init__(
        self,
        tif_configs: Optional[dict[tuple[Zone, int], TifConfig]] = None,
    ) -> None:
        self.tif_configs: dict[tuple[Zone, int], TifConfig] = tif_configs or {}

    def get_tif_config(self, timestamp: int, zone: Zone) -> Optional[TifConfig]:
        return self.tif_configs.get((zone, timestamp), None)


def create_tif(
    tif_path: str,
    tif_config: TifConfig,
    data: numpy.ndarray[Any, Any],
    no_data_value: Optional[float] = None,
) -> None:
    driver = gdal.GetDriverByName("GTiff")
    tif = driver.Create(
        tif_path,
        tif_config.cols,
        tif_config.rows,
        1,
        gdal.GDT_Float32,
        ["TILED=YES", "COMPRESS=LZW"],
    )
    band = tif.GetRasterBand(1)
    band.WriteArray(data, 0, 0)
    band.FlushCache()
    if no_data_value is not None:
        band.SetNoDataValue(no_data_value)

    tif.SetGeoTransform(tif_config.geo_transform)
    tif.SetProjection(tif_config.projection)
    tif.FlushCache()


class TifCreator(Protocol):
    def create_tif(
        self,
        tif_path: str,
        tif_config: TifConfig,
        data: numpy.ndarray[Any, Any],
        no_data_value: Optional[float] = None,
    ) -> None: ...


class RealTifCreator(TifCreator):
    def create_tif(
        self,
        tif_path: str,
        tif_config: TifConfig,
        data: numpy.ndarray[Any, Any],
        no_data_value: Optional[float] = None,
    ) -> None:
        create_tif(
            tif_path,
            tif_config,
            data,
            no_data_value,
        )


class InMemoryTifCreator(TifCreator):
    def __init__(self) -> None:
        self.tifs: dict[str, numpy.ndarray[Any, Any]] = {}

    def create_tif(
        self,
        tif_path: str,
        tif_config: TifConfig,
        data: numpy.ndarray[Any, Any],
        no_data_value: Optional[float] = None,
    ) -> None:
        self.tifs[tif_path] = data


def set_layer_at_timestamp_with_values_from(
    layer_index: int,
    tif_path: str,
    tif_config: TifConfig,
    accum_data: numpy.ndarray[Any, Any],
    *,
    tif_reader: TifReader,
) -> None:
    print(f"Reading [{tif_path}]...")
    dataset_at_timestamp = tif_reader.read_tif(tif_path)
    if dataset_at_timestamp is None:
        print(f"'{tif_path}' is None !")
        return

    accum_data[layer_index, :, :] = dataset_at_timestamp

    all_values_are_nan = numpy.all(numpy.isnan(accum_data[layer_index, :, :]))
    if all_values_are_nan:
        print(">> WARNING : all values in file are NaN ! Skipping that file.")
        accum_data[layer_index, :, :] = numpy.zeros(
            (tif_config.rows, tif_config.cols), numpy.float32
        )


def get_accumulations_per_timestamp_before_interpolation(
    zone: Zone,
    timestamps_before_interpolation: list[int],
    tif_config: TifConfig,
    *,
    tif_reader: TifReader,
):
    accumulations_per_timestamp: numpy.ndarray[Any, Any] = numpy.zeros(
        (len(timestamps_before_interpolation), tif_config.rows, tif_config.cols),
        numpy.float32,
    )

    start_time = time.time()
    layer_index_for_timestamp = 0
    for layer_index_for_timestamp, t in enumerate(timestamps_before_interpolation):
        cumul_5mn_val_tif_path = get_tif_path_for_param_in_zone_at(
            PrecipitationsParam.VALUES_5MN, zone, t
        )
        set_layer_at_timestamp_with_values_from(
            layer_index=layer_index_for_timestamp,
            tif_path=cumul_5mn_val_tif_path,
            tif_config=tif_config,
            accum_data=accumulations_per_timestamp,
            tif_reader=tif_reader,
        )

    print(f"Reading RGBA: {time.time()-start_time}s")
    print(accumulations_per_timestamp.shape)
    return accumulations_per_timestamp


def interpolate_accumulations_over_1h(
    timestamps_before_interpolation: list[int],
    timestamps_after_interpolation: list[int],
    accumulations_per_timestamp: numpy.ndarray[Any, Any],
):
    start_time = time.time()
    interpolator = interpolate.interp1d(
        timestamps_before_interpolation,
        accumulations_per_timestamp,
        axis=0,
        kind="cubic",
        copy=False,
        assume_sorted=True,
    )
    print(f"Interpolating mm/H: {time.time()-start_time}s")

    start_time = time.time()
    values = interpolator(timestamps_after_interpolation)
    print(f"Interpolating: {time.time()-start_time}s")
    return values


def integrate_accumulations_over_1h(
    timestamps_after_interpolation: list[int],
    values: numpy.ndarray[Any, Any],
):
    start_time = time.time()
    integrated = integrate.trapezoid(values, timestamps_after_interpolation, axis=0)
    print(f"Evaluating integral: {time.time()-start_time}s")
    return integrated / float(ONE_HOUR_IN_SECONDS)


def get_integrated_accumulations_over_1h(
    timestamp: int,
    timestamps_before_interpolation: list[int],
    accumulations_per_timestamp: numpy.ndarray[Any, Any],
):
    timestamps_after_interpolation = get_timestamps_for_interpolated_cumul_1h_at(
        timestamp
    )
    print("Interpolating to :")
    print([timestamp_to_iso(t) for t in timestamps_after_interpolation])

    interpolated = interpolate_accumulations_over_1h(
        timestamps_before_interpolation,
        timestamps_after_interpolation,
        accumulations_per_timestamp,
    )

    return integrate_accumulations_over_1h(
        timestamps_after_interpolation,
        interpolated,
    )


def create_accumulation_over_1h_from_instantanee_in_zone_at(
    zone: Zone,
    timestamp: int,
    tif_config: TifConfig,
    *,
    tif_reader: TifReader,
) -> numpy.ndarray[Any, Any]:
    timestamps_before_interpolation = get_timestamps_for_cumul_1h_at(timestamp)
    accumulations_per_timestamp = get_accumulations_per_timestamp_before_interpolation(
        zone,
        timestamps_before_interpolation,
        tif_config=tif_config,
        tif_reader=tif_reader,
    )
    print("Interpolating from :")
    print([timestamp_to_iso(t) for t in timestamps_before_interpolation])

    return get_integrated_accumulations_over_1h(
        timestamp,
        timestamps_before_interpolation,
        accumulations_per_timestamp,
    )


def generate_accumulations_over_1h_from_instantanee_in_zone_at(
    zone: Zone,
    timestamp: int,
    tif_config: TifConfig,
    *,
    tif_reader: TifReader,
    tif_creator: TifCreator,
    command_executor: CommandExecutor,
) -> None:
    print("Accumulation over 1h...")
    accumulation = create_accumulation_over_1h_from_instantanee_in_zone_at(
        zone,
        timestamp,
        tif_config,
        tif_reader=tif_reader,
    )

    cumul_1h_val_tif_ram_path = get_ram_path_for_param_in_zone_at(
        PrecipitationsParam.VALUES_1H, zone, timestamp
    )
    tif_creator.create_tif(
        cumul_1h_val_tif_ram_path,
        tif_config,
        accumulation,
        no_data_value=-99,
    )

    cumul_1h_color_tif_ram_path = get_ram_path_for_param_in_zone_at(
        PrecipitationsParam.COLOR_1H, zone, timestamp
    )
    generate_color_tif_from_values(
        cumul_1h_val_tif_ram_path,
        cumul_1h_color_tif_ram_path,
        AccumulationDuration.CUMUL_1H,
        command_executor=command_executor,
    )

    move_param_in_zone_at_from_ram_to_disk(
        PrecipitationsParam.VALUES_1H,
        zone,
        timestamp,
        command_executor=command_executor,
    )
    move_param_in_zone_at_from_ram_to_disk(
        PrecipitationsParam.COLOR_1H,
        zone,
        timestamp,
        command_executor=command_executor,
    )


def generate_accumulations_over_1h_from_instantanee_if_possible(
    zone: Zone,
    timestamp: int,
    tif_config: TifConfig,
    *,
    file_existence_checker: FileExistenceChecker,
    tif_reader: TifReader,
    tif_creator: TifCreator,
    command_executor: CommandExecutor,
    tiles_repository: TilesDatetimesRepository,
    replace_existing: bool = False,
) -> None:
    cumul_1h_color_tif_disk_path = get_tif_path_for_param_in_zone_at(
        PrecipitationsParam.COLOR_1H, zone, timestamp
    )
    if file_existence_checker.exists(cumul_1h_color_tif_disk_path):
        if not replace_existing:
            print(
                f"Skipping generation of accumulations over 1h because '{cumul_1h_color_tif_disk_path}' already exists."
            )
            return
        print(
            f"Replacing accumulations over 1h because '{cumul_1h_color_tif_disk_path}' already exists."
        )

    start_time = time.time()
    generate_accumulations_over_1h_from_instantanee_in_zone_at(
        zone,
        timestamp,
        tif_config,
        tif_reader=tif_reader,
        tif_creator=tif_creator,
        command_executor=command_executor,
    )
    if not replace_existing:
        update_tile_last_timestamp(
            PrecipitationsParam.COLOR_1H,
            zone,
            timestamp,
            repository=tiles_repository,
        )
    print(f"Took {time.time()-start_time} s.")


def create_accumulations_from(
    tifs_pathes: Iterable[str],
    tif_config: TifConfig,
    *,
    tif_reader: TifReader,
    transform: Transform,
) -> numpy.ndarray[Any, Any]:
    accumulations = numpy.zeros((tif_config.rows, tif_config.cols), numpy.float32)

    for tif_path in tifs_pathes:
        print(f"Processing '{tif_path}'...")
        dataset = tif_reader.read_tif(tif_path, transform=transform)
        if dataset is None:
            print(f"'{tif_path}' is None !")
            continue
        accumulations = accumulations + dataset

    return accumulations


def get_corresponding_values_precipitations_param(
    accumulation_duration: AccumulationDuration,
) -> PrecipitationsParam:
    if accumulation_duration == AccumulationDuration.CUMUL_1H:
        return PrecipitationsParam.VALUES_1H
    if accumulation_duration == AccumulationDuration.CUMUL_3H:
        return PrecipitationsParam.VALUES_3H
    if accumulation_duration == AccumulationDuration.CUMUL_6H:
        return PrecipitationsParam.VALUES_6H
    if accumulation_duration == AccumulationDuration.CUMUL_12H:
        return PrecipitationsParam.VALUES_12H
    if accumulation_duration == AccumulationDuration.CUMUL_24H:
        return PrecipitationsParam.VALUES_24H
    if accumulation_duration == AccumulationDuration.CUMUL_72H:
        return PrecipitationsParam.VALUES_72H
    raise ValueError(f"Unknown accumulation duration: {accumulation_duration}")


def get_corresponding_color_precipitations_param(
    accumulation_duration: AccumulationDuration,
) -> PrecipitationsParam:
    if accumulation_duration == AccumulationDuration.CUMUL_1H:
        return PrecipitationsParam.COLOR_1H
    if accumulation_duration == AccumulationDuration.CUMUL_3H:
        return PrecipitationsParam.COLOR_3H
    if accumulation_duration == AccumulationDuration.CUMUL_6H:
        return PrecipitationsParam.COLOR_6H
    if accumulation_duration == AccumulationDuration.CUMUL_12H:
        return PrecipitationsParam.COLOR_12H
    if accumulation_duration == AccumulationDuration.CUMUL_24H:
        return PrecipitationsParam.COLOR_24H
    if accumulation_duration == AccumulationDuration.CUMUL_72H:
        return PrecipitationsParam.COLOR_72H
    raise ValueError(f"Unknown accumulation duration: {accumulation_duration}")


def get_corresponding_transform(
    accumulation_duration: AccumulationDuration,
) -> Transform:
    if accumulation_duration == AccumulationDuration.CUMUL_1H:
        return MeteoFranceTransform()
    return IdentityTransform()


def get_accumulations_over_some_hours_in_zone_at(
    zone: Zone,
    timestamp: int,
    tif_config: TifConfig,
    accumulation_duration: AccumulationDuration,
    *,
    tif_reader: TifReader,
    transform: Transform,
) -> numpy.ndarray[Any, Any]:
    files_to_read = get_tifs_pathes_to_read_for_cumul_in_zone_at(
        zone, timestamp, accumulation_duration
    )
    return create_accumulations_from(
        files_to_read,
        tif_config,
        tif_reader=tif_reader,
        transform=transform,
    )


def should_keep_values_for(accumulation_duration: AccumulationDuration) -> bool:
    return accumulation_duration in [
        AccumulationDuration.CUMUL_1H,
        AccumulationDuration.CUMUL_24H,
        AccumulationDuration.CUMUL_72H,
    ]


def generate_accumulations_over_some_hours_in_zone_at(
    zone: Zone,
    timestamp: int,
    tif_config: TifConfig,
    accumulation_duration: AccumulationDuration,
    *,
    tif_reader: TifReader,
    transform: Transform,
    tif_creator: TifCreator,
    command_executor: CommandExecutor,
) -> None:
    print(f"Accumulation over {accumulation_duration.value}...")
    accumulations = get_accumulations_over_some_hours_in_zone_at(
        zone,
        timestamp,
        tif_config,
        accumulation_duration,
        tif_reader=tif_reader,
        transform=transform,
    )

    cumul_val_tif_ram_path = get_ram_path_for_param_in_zone_at(
        get_corresponding_values_precipitations_param(accumulation_duration),
        zone,
        timestamp,
    )
    tif_creator.create_tif(cumul_val_tif_ram_path, tif_config, accumulations)

    cumul_color_tif_ram_path = get_ram_path_for_param_in_zone_at(
        get_corresponding_color_precipitations_param(accumulation_duration),
        zone,
        timestamp,
    )
    generate_color_tif_from_values(
        cumul_val_tif_ram_path,
        cumul_color_tif_ram_path,
        accumulation_duration,
        command_executor=command_executor,
    )

    if should_keep_values_for(accumulation_duration):
        move_param_in_zone_at_from_ram_to_disk(
            get_corresponding_values_precipitations_param(accumulation_duration),
            zone,
            timestamp,
            command_executor=command_executor,
        )
    move_param_in_zone_at_from_ram_to_disk(
        get_corresponding_color_precipitations_param(accumulation_duration),
        zone,
        timestamp,
        command_executor=command_executor,
    )


def check_timestamp_eligibility_for(
    timestamp: int, accumulation_duration: AccumulationDuration
) -> Optional[str]:
    dt = get_datetime_from_timestamp(timestamp)
    if accumulation_duration == AccumulationDuration.CUMUL_1H:
        return (
            "0/5/10/15/20/25/30/35/40/45/50/55 in '{dt:%Y-%m-%d %H:%M:%S}'"
            if dt.minute % 5 != 0
            else None
        )
    if accumulation_duration in [
        AccumulationDuration.CUMUL_3H,
        AccumulationDuration.CUMUL_6H,
        AccumulationDuration.CUMUL_12H,
        AccumulationDuration.CUMUL_24H,
        AccumulationDuration.CUMUL_72H,
    ]:
        return f"0 in '{dt:%Y-%m-%d %H:%M:%S}'" if dt.minute != 0 else None
    raise ValueError(f"Unknown accumulation duration: {accumulation_duration}")


def generate_accumulations_over_some_hours_if_possible(
    zone: Zone,
    timestamp: int,
    tif_config: TifConfig,
    accumulation_duration: AccumulationDuration,
    *,
    file_existence_checker: FileExistenceChecker,
    tif_reader: TifReader,
    transform: Transform,
    tif_creator: TifCreator,
    command_executor: CommandExecutor,
    tiles_repository: TilesDatetimesRepository,
    replace_existing: bool = False,
) -> None:
    datetime_error = check_timestamp_eligibility_for(timestamp, accumulation_duration)
    if datetime_error:
        print(
            f"Skipping generation of accumulations over {accumulation_duration.value} because minutes are not {datetime_error}."
        )
        return

    cumul_color_tif_disk_path = get_tif_path_for_param_in_zone_at(
        get_corresponding_color_precipitations_param(accumulation_duration),
        zone,
        timestamp,
    )
    if file_existence_checker.exists(cumul_color_tif_disk_path):
        if not replace_existing:
            print(
                f"Skipping generation of accumulations over {accumulation_duration.value} because '{cumul_color_tif_disk_path}' already exists."
            )
            return
        print(
            f"Replacing accumulations over {accumulation_duration.value} because '{cumul_color_tif_disk_path}' already exists."
        )

    start_time = time.time()
    generate_accumulations_over_some_hours_in_zone_at(
        zone,
        timestamp,
        tif_config,
        accumulation_duration,
        tif_reader=tif_reader,
        transform=transform,
        tif_creator=tif_creator,
        command_executor=command_executor,
    )
    if not replace_existing:
        update_tile_last_timestamp(
            get_corresponding_color_precipitations_param(accumulation_duration),
            zone,
            timestamp,
            repository=tiles_repository,
        )
    print(f"Took {time.time()-start_time} s.")


def generate_accumulations(
    timestamp: int,
    zone: Zone,
    *,
    file_existence_checker: FileExistenceChecker,
    tif_config_getter: TifConfigGetter,
    tif_reader: TifReader,
    tif_creator: TifCreator,
    command_executor: CommandExecutor,
    tiles_repository: TilesDatetimesRepository,
    replace_existing: bool = False,
) -> None:
    tif_config: Optional[TifConfig] = None
    timestamp_for_config = timestamp
    while tif_config is None and timestamp_for_config > timestamp - ONE_HOUR_IN_SECONDS:
        tif_config = tif_config_getter.get_tif_config(timestamp_for_config, zone)
        timestamp_for_config -= FIVE_MINUTES_IN_SECONDS
    if tif_config is None:
        print(
            f"Skipping generation of accumulations because no tif found for zone '{zone}' at '{datetime_of(timestamp):%Y-%m-%d %H:%M:%S}'."
        )
        return

    accumulations_durations = [
        AccumulationDuration.CUMUL_1H,
        AccumulationDuration.CUMUL_3H,
        AccumulationDuration.CUMUL_6H,
        AccumulationDuration.CUMUL_12H,
        AccumulationDuration.CUMUL_24H,
        AccumulationDuration.CUMUL_72H,
    ]
    for accumulation_duration in accumulations_durations:
        generate_accumulations_over_some_hours_if_possible(
            zone,
            timestamp,
            tif_config,
            accumulation_duration,
            file_existence_checker=file_existence_checker,
            tif_reader=tif_reader,
            tif_creator=tif_creator,
            transform=get_corresponding_transform(accumulation_duration),
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=replace_existing,
        )


def execute_from_arguments(
    arguments: Arguments,
    *,
    file_existence_checker: FileExistenceChecker,
    tif_config_getter: TifConfigGetter,
    tif_reader: TifReader,
    tif_creator: TifCreator,
    command_executor: CommandExecutor,
    tiles_repository: TilesDatetimesRepository,
) -> None:
    for timestamp in range(
        arguments.start,
        arguments.end + FIVE_MINUTES_IN_SECONDS,
        FIVE_MINUTES_IN_SECONDS,
    ):
        for zone in arguments.zones:
            generate_accumulations(
                timestamp,
                zone,
                file_existence_checker=file_existence_checker,
                tif_config_getter=tif_config_getter,
                tif_reader=tif_reader,
                tif_creator=tif_creator,
                command_executor=command_executor,
                tiles_repository=tiles_repository,
                replace_existing=arguments.replace,
            )


def real_execute_from_arguments(arguments: Arguments) -> None:
    with get_sql_connection("V5") as connection:
        execute_from_arguments(
            arguments,
            file_existence_checker=RealFileExistenceChecker(),
            tif_config_getter=RealTifConfigGetter(),
            tif_reader=RealTifReader(),
            tif_creator=RealTifCreator(),
            command_executor=RealCommandExecutor(),
            tiles_repository=RealTilesDatetimesRepository(connection),
        )
