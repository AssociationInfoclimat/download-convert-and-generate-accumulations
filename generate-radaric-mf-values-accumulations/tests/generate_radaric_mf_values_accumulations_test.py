import unittest
from math import nan
from pathlib import Path

import numpy
from generate_radaric_mf_values_accumulations.datetime_utils import (
    FIVE_MINUTES_IN_SECONDS,
    ONE_HOUR_IN_SECONDS,
    get_timestamp_from_iso_utc_date,
)
from generate_radaric_mf_values_accumulations.generate_radaric_mf_values_accumulations import (
    IdentityTransform,
    InMemoryFileExistenceChecker,
    InMemoryTifConfigGetter,
    InMemoryTifCreator,
    InMemoryTifReader,
    MeteoFranceTransform,
    SameInMemoryTifReader,
    TifConfig,
    copy_from_disk_to_ram,
    copy_param_in_zone_at_from_disk_to_ram,
    create_accumulation_over_1h_from_instantanee_in_zone_at,
    create_accumulations_from,
    generate_accumulations,
    generate_accumulations_over_1h_from_instantanee_if_possible,
    generate_accumulations_over_1h_from_instantanee_in_zone_at,
    generate_accumulations_over_some_hours_if_possible,
    generate_accumulations_over_some_hours_in_zone_at,
    get_accumulations_over_some_hours_in_zone_at,
    get_accumulations_per_timestamp_before_interpolation,
    get_integrated_accumulations_over_1h,
    get_ram_path_for_param_in_zone_at,
    integrate_accumulations_over_1h,
    interpolate_accumulations_over_1h,
    move_from_ram_to_disk,
    move_param_in_zone_at_from_ram_to_disk,
    set_layer_at_timestamp_with_values_from,
)
from generate_radaric_mf_values_accumulations.radaric_mf_values_accumulations import (
    InMemoryCommandExecutor,
    get_timestamps_for_cumul_1h_at,
)
from generate_radaric_mf_values_accumulations.tiles import (
    AccumulationDuration,
    InMemoryTilesDatetimesRepository,
    PrecipitationsParam,
    Zone,
)

MEDIA_FS = "/media/datastore"
TILES_PATH = f"{MEDIA_FS}/tempsreel.infoclimat.net/tiles"


class TestGenerateRadaricMFValuesAccumulations(unittest.TestCase):

    maxDiff = None

    PALETTES_PATH = str(Path(__file__).parent.parent.parent / "palettes")

    def test_get_ram_path_for_param_in_zone_at(self) -> None:
        self.assertEqual(
            "/dev/shm/mosaiques_MF_LAME_D_EAU_METROPOLE_2000_06_15_12_30.tif",
            get_ram_path_for_param_in_zone_at(
                PrecipitationsParam.VALUES_5MN,
                Zone.METROPOLE,
                get_timestamp_from_iso_utc_date("2000-06-15T12:30:45Z"),
            ),
        )

    def test_move_from_ram_to_disk(self) -> None:
        ram_path = "/ram/path"
        disk_path = "/disk/path"
        command_executor = InMemoryCommandExecutor()
        move_from_ram_to_disk(
            ram_path,
            disk_path,
            command_executor=command_executor,
        )
        self.assertEqual(["mv /ram/path /disk/path"], command_executor.commands)

    def test_move_param_in_zone_at_from_ram_to_disk(self) -> None:
        param = PrecipitationsParam.VALUES_1H
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T12:30:45Z")
        command_executor = InMemoryCommandExecutor()
        move_param_in_zone_at_from_ram_to_disk(
            param,
            zone,
            timestamp,
            command_executor=command_executor,
        )
        self.assertEqual(
            [
                f"mv /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_12_30.tif {TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_12_v30.tif"
            ],
            command_executor.commands,
        )

    def test_copy_from_disk_to_ram(self) -> None:
        disk_path = "/disk/path"
        ram_path = "/ram/path"
        command_executor = InMemoryCommandExecutor()
        copy_from_disk_to_ram(
            disk_path,
            ram_path,
            command_executor=command_executor,
        )
        self.assertEqual(["cp /disk/path /ram/path"], command_executor.commands)

    def test_copy_param_in_zone_at_from_disk_to_ram(self) -> None:
        param = PrecipitationsParam.VALUES_1H
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T12:30:45Z")
        command_executor = InMemoryCommandExecutor()
        copy_param_in_zone_at_from_disk_to_ram(
            param,
            zone,
            timestamp,
            command_executor=command_executor,
        )
        self.assertEqual(
            [
                f"cp {TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_12_v30.tif /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_12_30.tif"
            ],
            command_executor.commands,
        )

    def test_setLayerAtTimestampWithValuesFrom_whenNoDataset(self) -> None:
        layer_index = 1
        tif_path = "/tif/path"
        tif_config = TifConfig(
            cols=3,
            rows=3,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        accum_data = numpy.array(
            [
                [
                    [1, 2, 3],
                    [4, 5, 6],
                    [7, 8, 9],
                ],
                [
                    [12, 11, 13],
                    [15, 14, 16],
                    [18, 17, 19],
                ],
                [
                    [101, 102, 103],
                    [104, 105, 106],
                    [107, 108, 109],
                ],
            ],
        )
        tif_reader = InMemoryTifReader()
        set_layer_at_timestamp_with_values_from(
            layer_index,
            tif_path,
            tif_config,
            accum_data,
            tif_reader=tif_reader,
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [
                            [1, 2, 3],
                            [4, 5, 6],
                            [7, 8, 9],
                        ],
                        [
                            [12, 11, 13],
                            [15, 14, 16],
                            [18, 17, 19],
                        ],
                        [
                            [101, 102, 103],
                            [104, 105, 106],
                            [107, 108, 109],
                        ],
                    ],
                ),
                accum_data,
            )
        )

    def test_setLayerAtTimestampWithValuesFrom_whenAllNaNDataset(self) -> None:
        layer_index = 1
        tif_path = "/tif/path"
        tif_config = TifConfig(
            cols=3,
            rows=3,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        accum_data = numpy.array(
            [
                [
                    [1, 2, 3],
                    [4, 5, 6],
                    [7, 8, 9],
                ],
                [
                    [12, 11, 13],
                    [15, 14, 16],
                    [18, 17, 19],
                ],
                [
                    [101, 102, 103],
                    [104, 105, 106],
                    [107, 108, 109],
                ],
            ],
            dtype=float,
        )
        tif_reader = InMemoryTifReader.from_list(
            {
                tif_path: [
                    [nan, nan, nan],
                    [nan, nan, nan],
                    [nan, nan, nan],
                ]
            }
        )
        set_layer_at_timestamp_with_values_from(
            layer_index,
            tif_path,
            tif_config,
            accum_data,
            tif_reader=tif_reader,
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [
                            [1, 2, 3],
                            [4, 5, 6],
                            [7, 8, 9],
                        ],
                        [
                            [0, 0, 0],
                            [0, 0, 0],
                            [0, 0, 0],
                        ],
                        [
                            [101, 102, 103],
                            [104, 105, 106],
                            [107, 108, 109],
                        ],
                    ],
                ),
                accum_data,
            )
        )

    def test_setLayerAtTimestampWithValuesFrom_whenSomeNaNDataset(self) -> None:
        layer_index = 1
        tif_path = "/tif/path"
        tif_config = TifConfig(
            cols=3,
            rows=3,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        accum_data = numpy.array(
            [
                [
                    [1, 2, 3],
                    [4, 5, 6],
                    [7, 8, 9],
                ],
                [
                    [12, 11, 13],
                    [15, 14, 16],
                    [18, 17, 19],
                ],
                [
                    [101, 102, 103],
                    [104, 105, 106],
                    [107, 108, 109],
                ],
            ],
            dtype=float,
        )
        tif_reader = InMemoryTifReader.from_list(
            {
                tif_path: [
                    [nan, 1, 1],
                    [2, nan, 2],
                    [3, 3, nan],
                ]
            }
        )
        set_layer_at_timestamp_with_values_from(
            layer_index,
            tif_path,
            tif_config,
            accum_data,
            tif_reader=tif_reader,
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [
                            [1, 2, 3],
                            [4, 5, 6],
                            [7, 8, 9],
                        ],
                        [
                            [nan, 1, 1],
                            [2, nan, 2],
                            [3, 3, nan],
                        ],
                        [
                            [101, 102, 103],
                            [104, 105, 106],
                            [107, 108, 109],
                        ],
                    ],
                    dtype=float,
                ),
                accum_data,
                equal_nan=True,
            )
        )

    def test_setLayerAtTimestampWithValuesFrom(self) -> None:
        layer_index = 1
        tif_path = "/tif/path"
        tif_config = TifConfig(
            cols=3,
            rows=3,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        accum_data = numpy.array(
            [
                [
                    [1, 2, 3],
                    [4, 5, 6],
                    [7, 8, 9],
                ],
                [
                    [12, 11, 13],
                    [15, 14, 16],
                    [18, 17, 19],
                ],
                [
                    [101, 102, 103],
                    [104, 105, 106],
                    [107, 108, 109],
                ],
            ],
        )
        tif_reader = InMemoryTifReader.from_list(
            {
                tif_path: [
                    [1, 1, 1],
                    [2, 2, 2],
                    [3, 3, 3],
                ]
            }
        )
        set_layer_at_timestamp_with_values_from(
            layer_index,
            tif_path,
            tif_config,
            accum_data,
            tif_reader=tif_reader,
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [
                            [1, 2, 3],
                            [4, 5, 6],
                            [7, 8, 9],
                        ],
                        [
                            [1, 1, 1],
                            [2, 2, 2],
                            [3, 3, 3],
                        ],
                        [
                            [101, 102, 103],
                            [104, 105, 106],
                            [107, 108, 109],
                        ],
                    ],
                ),
                accum_data,
            )
        )

    def test_get_accumulations_per_timestamp_before_interpolation(self) -> None:
        zone = Zone.METROPOLE
        timestamps_before_interpolation = [
            get_timestamp_from_iso_utc_date("2000-06-15T12:30:00Z"),
            get_timestamp_from_iso_utc_date("2000-06-15T12:35:00Z"),
            get_timestamp_from_iso_utc_date("2000-06-15T12:40:00Z"),
        ]
        tif_config = TifConfig(
            cols=3,
            rows=3,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        tif_reader = InMemoryTifReader.from_list(
            {
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v30.tif": [
                    [301, 302, 303],
                    [301, 302, 303],
                    [301, 302, 303],
                ],
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v35.tif": [
                    [351, 352, 353],
                    [351, 352, 353],
                    [351, 352, 353],
                ],
                f"{TILES_PATH}/2000/06/15/mosaiques_MF_LAME_D_EAU_METROPOLE_12_v40.tif": [
                    [401, 402, 403],
                    [401, 402, 403],
                    [401, 402, 403],
                ],
            }
        )
        accumulations = get_accumulations_per_timestamp_before_interpolation(
            zone,
            timestamps_before_interpolation,
            tif_config,
            tif_reader=tif_reader,
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [
                            [301, 302, 303],
                            [301, 302, 303],
                            [301, 302, 303],
                        ],
                        [
                            [351, 352, 353],
                            [351, 352, 353],
                            [351, 352, 353],
                        ],
                        [
                            [401, 402, 403],
                            [401, 402, 403],
                            [401, 402, 403],
                        ],
                    ],
                ),
                accumulations,
            )
        )

    def test_interpolate_accumulations_over_1h(self) -> None:
        timestamps_before_interpolation = [-3, -1, 1, 3]
        timestamps_after_interpolation = [-3, -2, -1, 0, 1, 2, 3]
        # [x^1, -2x^1]
        # [x^2, -2x^2]
        # [x^3, -2x^3]
        accumulations_per_timestamp = numpy.array(
            [
                [
                    [-3, 6],
                    [9, -18],
                    [-27, 54],
                ],
                [
                    [-1, 2],
                    [1, -2],
                    [-1, 2],
                ],
                [
                    [1, -2],
                    [1, -2],
                    [1, -2],
                ],
                [
                    [3, -6],
                    [9, -18],
                    [27, -54],
                ],
            ]
        )
        interpolated = interpolate_accumulations_over_1h(
            timestamps_before_interpolation,
            timestamps_after_interpolation,
            accumulations_per_timestamp,
        )
        self.assertTrue(
            numpy.allclose(
                numpy.array(
                    [
                        [
                            [-3, 6],
                            [9, -18],
                            [-27, 54],
                        ],
                        [
                            [-2, 4],
                            [4, -8],
                            [-8, 16],
                        ],
                        [
                            [-1, 2],
                            [1, -2],
                            [-1, 2],
                        ],
                        [
                            [0, 0],
                            [0, 0],
                            [0, 0],
                        ],
                        [
                            [1, -2],
                            [1, -2],
                            [1, -2],
                        ],
                        [
                            [2, -4],
                            [4, -8],
                            [8, -16],
                        ],
                        [
                            [3, -6],
                            [9, -18],
                            [27, -54],
                        ],
                    ]
                ),
                interpolated,
            )
        )

    def test_integrate_accumulations_over_1h(self) -> None:
        timestamps_after_interpolation = [0, 1, 4]
        values = numpy.array(
            [
                [
                    [1, 10],
                    [100, 1000],
                ],
                [
                    [2, 20],
                    [200, 2000],
                ],
                [
                    [3, 30],
                    [300, 3000],
                ],
            ]
        )
        integrated = integrate_accumulations_over_1h(timestamps_after_interpolation, values)
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [9 / ONE_HOUR_IN_SECONDS, 90 / ONE_HOUR_IN_SECONDS],
                        [900 / ONE_HOUR_IN_SECONDS, 9000 / ONE_HOUR_IN_SECONDS],
                    ]
                ),
                integrated,
            )
        )

    def test_get_integrated_accumulations_over_1h(self) -> None:
        """TODO: Fix the missing five minutes at the start, using the last value of the previous hour"""
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        timestamps_before_interpolation = get_timestamps_for_cumul_1h_at(timestamp)
        accumulations_per_timestamp = numpy.array(
            [
                [
                    [1, 2],
                    [3, 4],
                ]
                for _ in timestamps_before_interpolation
            ],
        )
        integrated = get_integrated_accumulations_over_1h(
            timestamp,
            timestamps_before_interpolation,
            accumulations_per_timestamp,
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [
                            (1 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                            (2 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                        ],
                        [
                            (3 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                            (4 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                        ],
                    ]
                ),
                integrated,
            )
        )

    def test_create_accumulation_over_1h_from_instantanee_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        integrated = create_accumulation_over_1h_from_instantanee_in_zone_at(
            zone,
            timestamp,
            tif_config,
            tif_reader=tif_reader,
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [
                            (1 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                            (2 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                        ],
                        [
                            (3 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                            (4 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                        ],
                    ]
                ),
                integrated,
            )
        )

    def test_generate_accumulations_over_1h_from_instantanee_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        generate_accumulations_over_1h_from_instantanee_in_zone_at(
            zone,
            timestamp,
            tif_config,
            tif_reader=tif_reader,
            tif_creator=tif_creator,
            command_executor=command_executor,
        )
        self.assertEqual(
            ["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [
                            (1 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                            (2 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                        ],
                        [
                            (3 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                            (4 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                        ],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar1h.cpt /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_13_v00.tif",
                f"mv /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/colorac60radaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )

    def test_generateAccumulationsOver1hFromInstantaneeIfPossible_whenAlreadyExisting(
        self,
    ) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        file_existence_checker = InMemoryFileExistenceChecker(
            {f"{TILES_PATH}/2000/06/15/colorac60radaric_MF_METROPOLE_13_v00.tif"}
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        tiles_repository = InMemoryTilesDatetimesRepository()
        generate_accumulations_over_1h_from_instantanee_if_possible(
            zone,
            timestamp,
            tif_config,
            file_existence_checker=file_existence_checker,
            tif_reader=tif_reader,
            tif_creator=tif_creator,
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=False,
        )
        self.assertEqual([], list(tif_creator.tifs.keys()))
        self.assertEqual([], command_executor.commands)
        self.assertEqual({}, tiles_repository.data)

    def test_generateAccumulationsOver1hFromInstantaneeIfPossible_whenReplacing(
        self,
    ) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        file_existence_checker = InMemoryFileExistenceChecker(
            {f"{TILES_PATH}/2000/06/15/colorac60radaric_MF_METROPOLE_13_v00.tif"}
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        tiles_repository = InMemoryTilesDatetimesRepository()
        generate_accumulations_over_1h_from_instantanee_if_possible(
            zone,
            timestamp,
            tif_config,
            file_existence_checker=file_existence_checker,
            tif_reader=tif_reader,
            tif_creator=tif_creator,
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=True,
        )
        self.assertEqual(
            ["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [
                            (1 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                            (2 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                        ],
                        [
                            (3 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                            (4 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                        ],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar1h.cpt /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_13_v00.tif",
                f"mv /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/colorac60radaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )
        self.assertEqual({}, tiles_repository.data)

    def test_generateAccumulationsOver1hFromInstantaneeIfPossible(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        file_existence_checker = InMemoryFileExistenceChecker()
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        tiles_repository = InMemoryTilesDatetimesRepository()
        generate_accumulations_over_1h_from_instantanee_if_possible(
            zone,
            timestamp,
            tif_config,
            file_existence_checker=file_existence_checker,
            tif_reader=tif_reader,
            tif_creator=tif_creator,
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=False,
        )
        self.assertEqual(
            ["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [
                            (1 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                            (2 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                        ],
                        [
                            (3 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                            (4 * (ONE_HOUR_IN_SECONDS - FIVE_MINUTES_IN_SECONDS))
                            / ONE_HOUR_IN_SECONDS,
                        ],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar1h.cpt /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_13_v00.tif",
                f"mv /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/colorac60radaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )
        self.assertEqual(
            {
                "colorac60radaric_MF_METROPOLE": {
                    "year": 2000,
                    "month": "06",
                    "day": "15",
                    "hour": "13",
                    "minute": "00",
                }
            },
            tiles_repository.data,
        )

    def test_create_accumulations_from(self) -> None:
        tifs_pathes = [
            "/tif/path/1",
            "/tif/path/2",
        ]
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        tif_reader = InMemoryTifReader.from_list(
            {
                "/tif/path/1": [
                    [1, 2],
                    [3, 4],
                ],
                "/tif/path/2": [
                    [5, 6],
                    [7, 8],
                ],
            }
        )
        accumulations = create_accumulations_from(
            tifs_pathes,
            tif_config,
            tif_reader=tif_reader,
            transform=IdentityTransform(),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 + 5, 2 + 6],
                        [3 + 7, 4 + 8],
                    ]
                ),
                accumulations,
            )
        )

    def test_get_accumulations_over_1h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [MeteoFranceTransform.METEOFRANCE_NO_DATA_VALUE, 2 * 100],
                [3 * 100, 4 * 100],
            ]
        )
        accumulations = get_accumulations_over_some_hours_in_zone_at(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_1H,
            tif_reader=tif_reader,
            transform=MeteoFranceTransform(),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [0 * 12, 2 * 12],
                        [3 * 12, 4 * 12],
                    ]
                ),
                accumulations,
            )
        )

    def test_generate_accumulations_over_1h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [MeteoFranceTransform.METEOFRANCE_NO_DATA_VALUE, 2 * 100],
                [3 * 100, 4 * 100],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        generate_accumulations_over_some_hours_in_zone_at(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_1H,
            tif_reader=tif_reader,
            transform=MeteoFranceTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
        )
        self.assertEqual(
            ["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [0 * 12, 2 * 12],
                        [3 * 12, 4 * 12],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar1h.cpt /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_13_v00.tif",
                f"mv /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/colorac60radaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )

    def test_generateAccumulationsOver1hIfPossible_whenWrongDatetime(
        self,
    ) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:01:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        file_existence_checker = InMemoryFileExistenceChecker()
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [MeteoFranceTransform.METEOFRANCE_NO_DATA_VALUE, 2 * 100],
                [3 * 100, 4 * 100],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        tiles_repository = InMemoryTilesDatetimesRepository()
        generate_accumulations_over_some_hours_if_possible(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_1H,
            file_existence_checker=file_existence_checker,
            tif_reader=tif_reader,
            transform=MeteoFranceTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=True,
        )
        self.assertEqual([], list(tif_creator.tifs.keys()))
        self.assertEqual([], command_executor.commands)
        self.assertEqual({}, tiles_repository.data)

    def test_generateAccumulationsOver1hIfPossible_whenAlreadyExisting(
        self,
    ) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        file_existence_checker = InMemoryFileExistenceChecker(
            {f"{TILES_PATH}/2000/06/15/colorac60radaric_MF_METROPOLE_13_v00.tif"}
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [MeteoFranceTransform.METEOFRANCE_NO_DATA_VALUE, 2 * 100],
                [3 * 100, 4 * 100],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        tiles_repository = InMemoryTilesDatetimesRepository()
        generate_accumulations_over_some_hours_if_possible(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_1H,
            file_existence_checker=file_existence_checker,
            tif_reader=tif_reader,
            transform=MeteoFranceTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=False,
        )
        self.assertEqual([], list(tif_creator.tifs.keys()))
        self.assertEqual([], command_executor.commands)
        self.assertEqual({}, tiles_repository.data)

    def test_generateAccumulationsOver1hIfPossible_whenReplacing(
        self,
    ) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        file_existence_checker = InMemoryFileExistenceChecker(
            {f"{TILES_PATH}/2000/06/15/colorac60radaric_MF_METROPOLE_13_v00.tif"}
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [MeteoFranceTransform.METEOFRANCE_NO_DATA_VALUE, 2 * 100],
                [3 * 100, 4 * 100],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        tiles_repository = InMemoryTilesDatetimesRepository()
        generate_accumulations_over_some_hours_if_possible(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_1H,
            file_existence_checker=file_existence_checker,
            tif_reader=tif_reader,
            transform=MeteoFranceTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=True,
        )
        self.assertEqual(
            ["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [0 * 12, 2 * 12],
                        [3 * 12, 4 * 12],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar1h.cpt /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_13_v00.tif",
                f"mv /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/colorac60radaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )
        self.assertEqual({}, tiles_repository.data)

    def test_generateAccumulationsOver1hIfPossible(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        file_existence_checker = InMemoryFileExistenceChecker()
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [MeteoFranceTransform.METEOFRANCE_NO_DATA_VALUE, 2 * 100],
                [3 * 100, 4 * 100],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        tiles_repository = InMemoryTilesDatetimesRepository()
        generate_accumulations_over_some_hours_if_possible(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_1H,
            file_existence_checker=file_existence_checker,
            tif_reader=tif_reader,
            transform=MeteoFranceTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=False,
        )
        self.assertEqual(
            ["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [0 * 12, 2 * 12],
                        [3 * 12, 4 * 12],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar1h.cpt /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_13_v00.tif",
                f"mv /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/colorac60radaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )
        self.assertEqual(
            {
                "colorac60radaric_MF_METROPOLE": {
                    "year": 2000,
                    "month": "06",
                    "day": "15",
                    "hour": "13",
                    "minute": "00",
                }
            },
            tiles_repository.data,
        )

    def test_generateAccumulationsOver3hIfPossible_whenWrongDatetime(
        self,
    ) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:30:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        file_existence_checker = InMemoryFileExistenceChecker()
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        tiles_repository = InMemoryTilesDatetimesRepository()
        generate_accumulations_over_some_hours_if_possible(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_3H,
            file_existence_checker=file_existence_checker,
            tif_reader=tif_reader,
            transform=IdentityTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=True,
        )
        self.assertEqual([], list(tif_creator.tifs.keys()))
        self.assertEqual([], command_executor.commands)
        self.assertEqual({}, tiles_repository.data)

    def test_get_accumulations_over_3h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        accumulations = get_accumulations_over_some_hours_in_zone_at(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_3H,
            tif_reader=tif_reader,
            transform=IdentityTransform(),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 3, 2 * 3],
                        [3 * 3, 4 * 3],
                    ]
                ),
                accumulations,
            )
        )

    def test_generate_accumulations_over_3h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        generate_accumulations_over_some_hours_in_zone_at(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_3H,
            tif_reader=tif_reader,
            transform=IdentityTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
        )
        self.assertEqual(
            ["/dev/shm/ac3hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 3, 2 * 3],
                        [3 * 3, 4 * 3],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac3hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac3hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar3h.cpt /dev/shm/ac3hradaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac3hradaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac3hradaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )

    def test_generateAccumulationsOver3hIfPossible_whenAlreadyExisting(
        self,
    ) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        file_existence_checker = InMemoryFileExistenceChecker(
            {f"{TILES_PATH}/2000/06/15/ac3hradaric_MF_METROPOLE_13_v00.tif"}
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        tiles_repository = InMemoryTilesDatetimesRepository()
        generate_accumulations_over_some_hours_if_possible(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_3H,
            file_existence_checker=file_existence_checker,
            tif_reader=tif_reader,
            transform=IdentityTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=False,
        )
        self.assertEqual([], list(tif_creator.tifs.keys()))
        self.assertEqual([], command_executor.commands)
        self.assertEqual({}, tiles_repository.data)

    def test_generateAccumulationsOver3hIfPossible_whenReplacing(
        self,
    ) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        file_existence_checker = InMemoryFileExistenceChecker(
            {f"{TILES_PATH}/2000/06/15/ac3hradaric_MF_METROPOLE_13_v00.tif"}
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        tiles_repository = InMemoryTilesDatetimesRepository()
        generate_accumulations_over_some_hours_if_possible(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_3H,
            file_existence_checker=file_existence_checker,
            tif_reader=tif_reader,
            transform=IdentityTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=True,
        )
        self.assertEqual(
            ["/dev/shm/ac3hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 3, 2 * 3],
                        [3 * 3, 4 * 3],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac3hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac3hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar3h.cpt /dev/shm/ac3hradaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac3hradaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac3hradaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )
        self.assertEqual({}, tiles_repository.data)

    def test_generateAccumulationsOver3hIfPossible(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        file_existence_checker = InMemoryFileExistenceChecker()
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        tiles_repository = InMemoryTilesDatetimesRepository()
        generate_accumulations_over_some_hours_if_possible(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_3H,
            file_existence_checker=file_existence_checker,
            tif_reader=tif_reader,
            transform=IdentityTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=False,
        )
        self.assertEqual(
            ["/dev/shm/ac3hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 3, 2 * 3],
                        [3 * 3, 4 * 3],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac3hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac3hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar3h.cpt /dev/shm/ac3hradaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac3hradaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac3hradaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )
        self.assertEqual(
            {
                "ac3hradaric_MF_METROPOLE": {
                    "year": 2000,
                    "month": "06",
                    "day": "15",
                    "hour": "13",
                    "minute": "00",
                }
            },
            tiles_repository.data,
        )

    def test_generate_accumulations_over_6h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        generate_accumulations_over_some_hours_in_zone_at(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_6H,
            tif_reader=tif_reader,
            transform=IdentityTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
        )
        self.assertEqual(
            ["/dev/shm/ac6hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 6, 2 * 6],
                        [3 * 6, 4 * 6],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac6hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac6hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar6h.cpt /dev/shm/ac6hradaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac6hradaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac6hradaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )

    def test_generate_accumulations_over_12h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        generate_accumulations_over_some_hours_in_zone_at(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_12H,
            tif_reader=tif_reader,
            transform=IdentityTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
        )
        self.assertEqual(
            ["/dev/shm/ac12hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 12, 2 * 12],
                        [3 * 12, 4 * 12],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac12hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac12hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar12h.cpt /dev/shm/ac12hradaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac12hradaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac12hradaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )

    def test_generate_accumulations_over_24h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        generate_accumulations_over_some_hours_in_zone_at(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_24H,
            tif_reader=tif_reader,
            transform=IdentityTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
        )
        self.assertEqual(
            ["/dev/shm/ac24hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 24, 2 * 24],
                        [3 * 24, 4 * 24],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac24hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac24hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar24h.cpt /dev/shm/ac24hradaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac24hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac24hradaricval_MF_METROPOLE_13_v00.tif",
                f"mv /dev/shm/ac24hradaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac24hradaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )

    def test_generate_accumulations_over_72h_in_zone_at(self) -> None:
        zone = Zone.METROPOLE
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        tif_config = TifConfig(
            cols=2,
            rows=2,
            geo_transform=(0, 1, 0, 0, 0, 1),
            projection="Test",
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        generate_accumulations_over_some_hours_in_zone_at(
            zone,
            timestamp,
            tif_config,
            AccumulationDuration.CUMUL_72H,
            tif_reader=tif_reader,
            transform=IdentityTransform(),
            tif_creator=tif_creator,
            command_executor=command_executor,
        )
        self.assertEqual(
            ["/dev/shm/ac72hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 3, 2 * 3],
                        [3 * 3, 4 * 3],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac72hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac72hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar72h.cpt /dev/shm/ac72hradaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac72hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac72hradaricval_MF_METROPOLE_13_v00.tif",
                f"mv /dev/shm/ac72hradaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac72hradaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )

    def test_generate_accumulations(self) -> None:
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T13:00:00Z")
        zone = Zone.METROPOLE
        file_existence_checker = InMemoryFileExistenceChecker()
        tif_config_getter = InMemoryTifConfigGetter(
            {
                (zone, timestamp): TifConfig(
                    cols=2,
                    rows=2,
                    geo_transform=(0, 1, 0, 0, 0, 1),
                    projection="Test",
                )
            }
        )
        tif_reader = SameInMemoryTifReader.from_list(
            [
                [1, 2],
                [3, 4],
            ]
        )
        tif_creator = InMemoryTifCreator()
        command_executor = InMemoryCommandExecutor()
        tiles_repository = InMemoryTilesDatetimesRepository()
        generate_accumulations(
            timestamp,
            zone,
            file_existence_checker=file_existence_checker,
            tif_config_getter=tif_config_getter,
            tif_reader=tif_reader,
            tif_creator=tif_creator,
            command_executor=command_executor,
            tiles_repository=tiles_repository,
            replace_existing=False,
        )
        self.assertEqual(
            [
                "/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif",
                "/dev/shm/ac3hradaricval_MF_METROPOLE_2000_06_15_13_00.tif",
                "/dev/shm/ac6hradaricval_MF_METROPOLE_2000_06_15_13_00.tif",
                "/dev/shm/ac12hradaricval_MF_METROPOLE_2000_06_15_13_00.tif",
                "/dev/shm/ac24hradaricval_MF_METROPOLE_2000_06_15_13_00.tif",
                "/dev/shm/ac72hradaricval_MF_METROPOLE_2000_06_15_13_00.tif",
            ],
            list(tif_creator.tifs.keys()),
        )
        self.assertTrue(
            numpy.allclose(
                numpy.array(
                    [
                        [1 / 100 * 12, 2 / 100 * 12],
                        [3 / 100 * 12, 4 / 100 * 12],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif"],
                atol=1e-10,
                rtol=0,
            )
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 3, 2 * 3],
                        [3 * 3, 4 * 3],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac3hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 6, 2 * 6],
                        [3 * 6, 4 * 6],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac6hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 12, 2 * 12],
                        [3 * 12, 4 * 12],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac12hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 24, 2 * 24],
                        [3 * 24, 4 * 24],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac24hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertTrue(
            numpy.array_equal(
                numpy.array(
                    [
                        [1 * 3, 2 * 3],
                        [3 * 3, 4 * 3],
                    ]
                ),
                tif_creator.tifs["/dev/shm/ac72hradaricval_MF_METROPOLE_2000_06_15_13_00.tif"],
            )
        )
        self.assertEqual(
            [
                f"gdaldem color-relief /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar1h.cpt /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac60radaric_MF_METROPOLE_13_v00.tif",
                f"mv /dev/shm/colorac60radaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/colorac60radaric_MF_METROPOLE_13_v00.tif",
                f"gdaldem color-relief /dev/shm/ac3hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar3h.cpt /dev/shm/ac3hradaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac3hradaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac3hradaric_MF_METROPOLE_13_v00.tif",
                f"gdaldem color-relief /dev/shm/ac6hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar6h.cpt /dev/shm/ac6hradaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac6hradaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac6hradaric_MF_METROPOLE_13_v00.tif",
                f"gdaldem color-relief /dev/shm/ac12hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar12h.cpt /dev/shm/ac12hradaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac12hradaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac12hradaric_MF_METROPOLE_13_v00.tif",
                f"gdaldem color-relief /dev/shm/ac24hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar24h.cpt /dev/shm/ac24hradaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac24hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac24hradaricval_MF_METROPOLE_13_v00.tif",
                f"mv /dev/shm/ac24hradaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac24hradaric_MF_METROPOLE_13_v00.tif",
                f"gdaldem color-relief /dev/shm/ac72hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {self.PALETTES_PATH}/radar72h.cpt /dev/shm/ac72hradaric_MF_METROPOLE_2000_06_15_13_00.tif -alpha -nearest_color_entry -of COG -co 'COMPRESS=LZW' -co 'PREDICTOR=YES'",
                f"mv /dev/shm/ac72hradaricval_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac72hradaricval_MF_METROPOLE_13_v00.tif",
                f"mv /dev/shm/ac72hradaric_MF_METROPOLE_2000_06_15_13_00.tif {TILES_PATH}/2000/06/15/ac72hradaric_MF_METROPOLE_13_v00.tif",
            ],
            command_executor.commands,
        )


if __name__ == "__main__":
    unittest.main()
