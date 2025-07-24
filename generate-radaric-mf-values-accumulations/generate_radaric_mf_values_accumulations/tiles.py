import json
from enum import Enum
from typing import Protocol

from sqlalchemy import Connection

from .datetime_utils import (
    get_date_object_for,
    get_datetime_from_timestamp,
    get_timestamp_from_json_date,
)
from .sql import execute_and_commit_sql, execute_sql, get_sql_connection

MEDIA_FS = '/media/datastore'
TILES_PATH = MEDIA_FS + '/tempsreel.infoclimat.net/tiles'

class Zone(Enum):
    METROPOLE = "METROPOLE"
    ANTILLES = "ANTILLES"
    REUNION = "REUNION"
    NOUVELLE_CALEDONIE = "NOUVELLE-CALEDONIE"


class AccumulationDuration(Enum):
    CUMUL_5MN = "5mn"
    CUMUL_1H = "1h"
    CUMUL_3H = "3h"
    CUMUL_6H = "6h"
    CUMUL_12H = "12h"
    CUMUL_24H = "24h"
    CUMUL_72H = "72h"


class PrecipitationsParam(Enum):
    VALUES_5MN = "mosaiques_MF_LAME_D_EAU"
    COLOR_5MN = "radaric_MF"
    VALUES_1H = "ac60radaric_MF"
    COLOR_1H = "colorac60radaric_MF"
    VALUES_3H = "ac3hradaricval_MF"
    COLOR_3H = "ac3hradaric_MF"
    VALUES_6H = "ac6hradaricval_MF"
    COLOR_6H = "ac6hradaric_MF"
    VALUES_12H = "ac12hradaricval_MF"
    COLOR_12H = "ac12hradaric_MF"
    VALUES_24H = "ac24hradaricval_MF"
    COLOR_24H = "ac24hradaric_MF"
    VALUES_72H = "ac72hradaricval_MF"
    COLOR_72H = "ac72hradaric_MF"


def update_tile_last_date_object_using(
    connection: Connection, key: str, data: dict[str, str]
) -> None:
    execute_and_commit_sql(
        connection,
        """
            REPLACE INTO V5.cartes_tuiles
            VALUES (:nom, :donnees)
        """,
        {"nom": key, "donnees": json.dumps(data)},
    )


def update_tile_last_date_object(key: str, data: dict[str, str]) -> None:
    with get_sql_connection("V5") as connection:
        update_tile_last_date_object_using(connection, key, data)


class TilesDatetimesRepository(Protocol):
    def update_tile_last_date_object(
        self, key: str, data: dict[str, str]
    ) -> None:
        ...


class RealTilesDatetimesRepository(TilesDatetimesRepository):
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def update_tile_last_date_object(
        self, key: str, data: dict[str, str]
    ) -> None:
        update_tile_last_date_object_using(self.connection, key, data)


class InMemoryTilesDatetimesRepository(TilesDatetimesRepository):
    def __init__(self) -> None:
        self.data: dict[str, dict[str, str]] = {}

    def update_tile_last_date_object(
        self, key: str, data: dict[str, str]
    ) -> None:
        self.data[key] = data


def update_last_timestamp_for(key: str, timestamp: int) -> None:
    date_object = get_date_object_for(timestamp)
    update_tile_last_date_object(key, date_object)


def get_param_key_for_zone(param: PrecipitationsParam, zone: Zone) -> str:
    return f"{param.value}_{zone.value}"


def update_tile_last_timestamp(
    param: PrecipitationsParam,
    zone: Zone,
    timestamp: int,
    *,
    repository: TilesDatetimesRepository,
) -> None:
    param_key = get_param_key_for_zone(param, zone)
    date_object = get_date_object_for(timestamp)
    repository.update_tile_last_date_object(param_key, date_object)


def get_last_tiles_timestamps() -> dict[str, int]:
    with get_sql_connection("V5") as connection:
        cursor = execute_sql(
            connection,
            """
                SELECT
                    nom,
                    donnees
                FROM V5.cartes_tuiles
            """,
        )
        timestamps: dict[str, int] = {
            nom: get_timestamp_from_json_date(donnees) for (nom, donnees) in cursor
        }
    return timestamps


def get_tif_path_for_param_in_zone_at(
    param: PrecipitationsParam, zone: Zone, timestamp: int
) -> str:
    dt = get_datetime_from_timestamp(timestamp)
    param_key = get_param_key_for_zone(param, zone)
    return f"{TILES_PATH}/{dt.year:04d}/{dt.month:02d}/{dt.day:02d}/{param_key}_{dt.hour:02d}_v{dt.minute:02d}.tif"
