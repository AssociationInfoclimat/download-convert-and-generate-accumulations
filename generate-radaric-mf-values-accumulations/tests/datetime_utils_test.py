import datetime
import unittest

from generate_radaric_mf_values_accumulations.datetime_utils import (
    datetime_of,
    get_date_object_for,
    get_datetime_from_date_object,
    get_datetime_from_timestamp,
    get_timestamp_from_iso_utc_date,
    get_timestamp_from_json_date,
    timestamp_of,
    timestamp_to_iso,
    to_iso,
)


class TestDatetimeUtils(unittest.TestCase):
    maxDiff = None

    def test_get_timestamp_from_iso_utc_date(self) -> None:
        self.assertEqual(
            961072245, get_timestamp_from_iso_utc_date("2000-06-15T12:30:45Z")
        )
        self.assertEqual(
            961072245, get_timestamp_from_iso_utc_date("2000-06-15 12:30:45")
        )

    def test_timestamp_of(self) -> None:
        self.assertEqual(961072245, timestamp_of("2000-06-15T12:30:45Z"))
        self.assertEqual(961072245, timestamp_of("2000-06-15 12:30:45"))

    def test_get_datetime_from_timestamp(self) -> None:
        dt = get_datetime_from_timestamp(961072245)
        self.assertEqual(2000, dt.year)
        self.assertEqual(6, dt.month)
        self.assertEqual(15, dt.day)
        self.assertEqual(12, dt.hour)
        self.assertEqual(30, dt.minute)
        self.assertEqual(45, dt.second)
        self.assertEqual(datetime.timezone.utc, dt.tzinfo)

    def test_datetime_of(self) -> None:
        dt = datetime_of(961072245)
        self.assertEqual(2000, dt.year)
        self.assertEqual(6, dt.month)
        self.assertEqual(15, dt.day)
        self.assertEqual(12, dt.hour)
        self.assertEqual(30, dt.minute)
        self.assertEqual(45, dt.second)
        self.assertEqual(datetime.timezone.utc, dt.tzinfo)

    def test_to_iso(self) -> None:
        dt = datetime_of(961072245)
        self.assertEqual("2000-06-15T12:30:45Z", to_iso(dt))

    def test_timestamp_to_iso(self) -> None:
        self.assertEqual("2000-06-15T12:30:45Z", timestamp_to_iso(961072245))

    def test_date_object_for(self) -> None:
        timestamp = get_timestamp_from_iso_utc_date("2000-06-15T12:30:45Z")
        self.assertEqual(
            {
                "year": 2000,
                "month": "06",
                "day": "15",
                "hour": "12",
                "minute": "30",
            },
            get_date_object_for(timestamp),
        )

    def test_get_datetime_from_date_object(self) -> None:
        dt = get_datetime_from_date_object(
            {
                "year": 2000,
                "month": "06",
                "day": "15",
                "hour": "12",
                "minute": "30",
            }
        )
        self.assertEqual(2000, dt.year)
        self.assertEqual(6, dt.month)
        self.assertEqual(15, dt.day)
        self.assertEqual(12, dt.hour)
        self.assertEqual(30, dt.minute)
        self.assertEqual(0, dt.second)
        self.assertEqual(datetime.timezone.utc, dt.tzinfo)

    def test_get_timestamp_from_json_date(self) -> None:
        dt = get_timestamp_from_json_date(
            """
                {
                    "year": 2000,
                    "month": "06",
                    "day": "15",
                    "hour": "12",
                    "minute": "30"
                }
            """
        )
        self.assertEqual(961072200, dt)  # 961072200 -> '2000-06-15T12:30:00Z'


if __name__ == "__main__":
    unittest.main()
