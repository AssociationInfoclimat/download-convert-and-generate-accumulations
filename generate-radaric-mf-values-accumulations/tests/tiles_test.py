import unittest

from generate_radaric_mf_values_accumulations.datetime_utils import (
    get_timestamp_from_iso_utc_date,
)
from generate_radaric_mf_values_accumulations.tiles import (
    InMemoryTilesDatetimesRepository,
    PrecipitationsParam,
    Zone,
    get_param_key_for_zone,
    get_tif_path_for_param_in_zone_at,
    update_tile_last_timestamp,
)

MEDIA_FS = '/media/datastore'
TILES_PATH = f"{MEDIA_FS}/tempsreel.infoclimat.net/tiles"

class TestTiles(unittest.TestCase):
    maxDiff = None

    def test_get_param_key_for_zone(self) -> None:
        self.assertEqual(
            "mosaiques_MF_LAME_D_EAU_METROPOLE",
            get_param_key_for_zone(PrecipitationsParam.VALUES_5MN, Zone.METROPOLE),
        )
        self.assertEqual(
            "radaric_MF_NOUVELLE-CALEDONIE",
            get_param_key_for_zone(
                PrecipitationsParam.COLOR_5MN, Zone.NOUVELLE_CALEDONIE
            ),
        )

    def test_update_tile_last_timestamp(self) -> None:
        param = PrecipitationsParam.COLOR_5MN
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T12:30:45Z")
        repository = InMemoryTilesDatetimesRepository()
        timestamp = update_tile_last_timestamp(
            param,
            zone,
            timestamp,
            repository=repository,
        )
        self.assertEqual(
            {
                "radaric_MF_METROPOLE": {
                    "year": 2000,
                    "month": "06",
                    "day": "15",
                    "hour": "12",
                    "minute": "30",
                }
            },
            repository.data,
        )

    def test_get_tif_path_for_param_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T12:30:45Z")
        self.assertEqual(
            f"{TILES_PATH}/2000/06/15/radaric_MF_METROPOLE_12_v30.tif",
            get_tif_path_for_param_in_zone_at(
                PrecipitationsParam.COLOR_5MN, zone, timestamp
            ),
        )


if __name__ == "__main__":
    unittest.main()
