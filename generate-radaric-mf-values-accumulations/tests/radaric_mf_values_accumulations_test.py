import unittest
from pathlib import Path

from generate_radaric_mf_values_accumulations.datetime_utils import (
    FIVE_MINUTES_IN_SECONDS,
    get_timestamp_from_iso_utc_date,
)
from generate_radaric_mf_values_accumulations.radaric_mf_values_accumulations import (
    InMemoryCommandExecutor,
    Zone,
    generate_color_tif_from_values,
    get_accumulation_range,
    get_generate_color_tif_from_values_command,
    get_palette_file_path_for,
    get_radar_palette_file_path_for,
    get_range,
    get_tifs_pathes_to_read_for_cumul_1h_in_zone_at,
    get_tifs_pathes_to_read_for_cumul_3h_in_zone_at,
    get_tifs_pathes_to_read_for_cumul_6h_in_zone_at,
    get_tifs_pathes_to_read_for_cumul_12h_in_zone_at,
    get_tifs_pathes_to_read_for_cumul_24h_in_zone_at,
    get_tifs_pathes_to_read_for_cumul_72h_in_zone_at,
    get_timestamps_for_cumul_1h_at,
    get_timestamps_for_interpolated_cumul_1h_at,
)
from generate_radaric_mf_values_accumulations.tiles import AccumulationDuration

MEDIA_FS = "/media/datastore"
TILES_PATH = f"{MEDIA_FS}/tempsreel.infoclimat.net/tiles"


class TestRadaricMFValuesAccumulations(unittest.TestCase):

    maxDiff = None

    PALETTES_PATH = str(Path(__file__).parent.parent.parent / "palettes")

    def test_get_range(self) -> None:
        start = 0
        end = 20
        step = 5
        self.assertEqual(
            [0, 5, 10, 15, 20],
            list(get_range(start, end, step, exclude_start=False, exclude_end=False)),
        )
        self.assertEqual(
            [0, 5, 10, 15],
            list(get_range(start, end, step, exclude_start=False, exclude_end=True)),
        )
        self.assertEqual(
            [5, 10, 15, 20],
            list(get_range(start, end, step, exclude_start=True, exclude_end=False)),
        )
        self.assertEqual(
            [5, 10, 15],
            list(get_range(start, end, step, exclude_start=True, exclude_end=True)),
        )

    def test_get_accumulation_range(self) -> None:
        start = get_timestamp_from_iso_utc_date("2000-06-15T12:00:00Z")
        end = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        step = FIVE_MINUTES_IN_SECONDS
        self.assertEqual(
            [
                get_timestamp_from_iso_utc_date("2000-06-15T12:05:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:10:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:15:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:20:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:25:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:30:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:35:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:40:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:45:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:50:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:55:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z"),
            ],
            list(get_accumulation_range(start, end, step)),
        )

    def test_get_timestamps_for_cumul_1h_at(self) -> None:
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        self.assertEqual(
            [
                get_timestamp_from_iso_utc_date("2000-06-15T12:05:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:10:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:15:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:20:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:25:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:30:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:35:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:40:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:45:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:50:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:55:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z"),
            ],
            get_timestamps_for_cumul_1h_at(timestamp),
        )

    def test_get_timestamps_for_interpolated_cumul_1h_at(self) -> None:
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        timestamps = get_timestamps_for_interpolated_cumul_1h_at(timestamp)
        self.assertEqual(
            [
                get_timestamp_from_iso_utc_date("2000-06-15T12:05:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:06:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:07:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:08:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:09:00Z"),
            ],
            timestamps[:5],
        )
        self.assertEqual(
            [
                get_timestamp_from_iso_utc_date("2000-06-15T12:56:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:57:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:58:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T12:59:00Z"),
                get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z"),
            ],
            timestamps[-5:],
        )

    def test_get_tifs_pathes_to_read_for_cumul_1h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T12:00:00Z")
        self.assertEqual(
            [
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_11_v05.tif",
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_11_v10.tif",
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_11_v15.tif",
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_11_v20.tif",
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_11_v25.tif",
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_11_v30.tif",
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_11_v35.tif",
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_11_v40.tif",
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_11_v45.tif",
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_11_v50.tif",
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_11_v55.tif",
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v00.tif",
            ],
            list(get_tifs_pathes_to_read_for_cumul_1h_in_zone_at(zone, timestamp)),
        )

    def test_get_tifs_pathes_to_read_for_cumul_3h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T12:00:00Z")
        self.assertEqual(
            [
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_10_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_11_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_12_v00.tif",
            ],
            list(get_tifs_pathes_to_read_for_cumul_3h_in_zone_at(zone, timestamp)),
        )

    def test_get_tifs_pathes_to_read_for_cumul_6h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T12:00:00Z")
        self.assertEqual(
            [
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_07_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_08_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_09_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_10_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_11_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_12_v00.tif",
            ],
            list(get_tifs_pathes_to_read_for_cumul_6h_in_zone_at(zone, timestamp)),
        )

    def test_get_tifs_pathes_to_read_for_cumul_12h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T12:00:00Z")
        self.assertEqual(
            [
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_01_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_02_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_03_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_04_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_05_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_06_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_07_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_08_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_09_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_10_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_11_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_12_v00.tif",
            ],
            list(get_tifs_pathes_to_read_for_cumul_12h_in_zone_at(zone, timestamp)),
        )

    def test_get_tifs_pathes_to_read_for_cumul_24h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T12:00:00Z")
        self.assertEqual(
            [
                f"{TILES_PATH}/2000/06/14/ac60radaric_MF_METROPOLE_13_v00.tif",
                f"{TILES_PATH}/2000/06/14/ac60radaric_MF_METROPOLE_14_v00.tif",
                f"{TILES_PATH}/2000/06/14/ac60radaric_MF_METROPOLE_15_v00.tif",
                f"{TILES_PATH}/2000/06/14/ac60radaric_MF_METROPOLE_16_v00.tif",
                f"{TILES_PATH}/2000/06/14/ac60radaric_MF_METROPOLE_17_v00.tif",
                f"{TILES_PATH}/2000/06/14/ac60radaric_MF_METROPOLE_18_v00.tif",
                f"{TILES_PATH}/2000/06/14/ac60radaric_MF_METROPOLE_19_v00.tif",
                f"{TILES_PATH}/2000/06/14/ac60radaric_MF_METROPOLE_20_v00.tif",
                f"{TILES_PATH}/2000/06/14/ac60radaric_MF_METROPOLE_21_v00.tif",
                f"{TILES_PATH}/2000/06/14/ac60radaric_MF_METROPOLE_22_v00.tif",
                f"{TILES_PATH}/2000/06/14/ac60radaric_MF_METROPOLE_23_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_00_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_01_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_02_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_03_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_04_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_05_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_06_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_07_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_08_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_09_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_10_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_11_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_12_v00.tif",
            ],
            list(get_tifs_pathes_to_read_for_cumul_24h_in_zone_at(zone, timestamp)),
        )

    def test_get_tifs_pathes_to_read_for_cumul_72h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T12:00:00Z")
        self.assertEqual(
            [
                f"{TILES_PATH}/2000/06/13/ac24hradaricval_MF_METROPOLE_12_v00.tif",
                f"{TILES_PATH}/2000/06/14/ac24hradaricval_MF_METROPOLE_12_v00.tif",
                f"{TILES_PATH}/2000/06/15/ac24hradaricval_MF_METROPOLE_12_v00.tif",
            ],
            list(get_tifs_pathes_to_read_for_cumul_72h_in_zone_at(zone, timestamp)),
        )

    def test_get_palette_file_path_for(self) -> None:
        self.assertEqual(
            f"{self.PALETTES_PATH}/palette_name.cpt",
            get_palette_file_path_for("palette_name"),
        )

    def test_get_radar_palette_file_path_for(self) -> None:
        self.assertEqual(
            f"{self.PALETTES_PATH}/radar1h.cpt",
            get_radar_palette_file_path_for(AccumulationDuration.CUMUL_1H),
        )

    def test_get_generate_color_tif_from_values_command_for(self) -> None:
        self.assertEqual(
            "gdaldem color-relief /values/tif/path.tif /palette/path.cpt /color/tif/path.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
            get_generate_color_tif_from_values_command(
                "/values/tif/path.tif", "/color/tif/path.tif", "/palette/path.cpt"
            ),
        )

    def test_generate_color_tif_from_values(self) -> None:
        command_executor = InMemoryCommandExecutor()
        generate_color_tif_from_values(
            "/values/tif/path.tif",
            "/color/tif/path.tif",
            AccumulationDuration.CUMUL_1H,
            command_executor=command_executor,
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /values/tif/path.tif {self.PALETTES_PATH}/radar1h.cpt /color/tif/path.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'"
            ],
            command_executor.commands,
        )


if __name__ == "__main__":
    unittest.main()
