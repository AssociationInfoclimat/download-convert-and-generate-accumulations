import argparse
import unittest

from generate_radaric_mf_values_accumulations.arguments import ZONES, parse_arguments
from generate_radaric_mf_values_accumulations.tiles import Zone


class TestArguments(unittest.TestCase):
    maxDiff = None

    def test_parseArguments_whenEmpty(self) -> None:
        """
        error: one of the arguments --timestamp --datetime is required
        """
        with self.assertRaises(SystemExit) as cm:
            parse_arguments([])
        self.assertEqual(2, cm.exception.code)
        print(cm.exception)

    def test_parseArguments_whenTimestamp(self) -> None:
        arguments = parse_arguments(["--timestamp", "961072245"])
        self.assertEqual(961072245, arguments.start)
        self.assertEqual(961072245, arguments.end)

    def test_parseArguments_whenDatetimeISO(self) -> None:
        arguments = parse_arguments(["--datetime", "2000-06-15T12:30:45Z"])
        self.assertEqual(961072245, arguments.start)
        self.assertEqual(961072245, arguments.end)

    def test_parseArguments_whenDatetimeAmbiguous(self) -> None:
        arguments = parse_arguments(["--datetime", "2000-06-15 12:30:45"])
        self.assertEqual(961072245, arguments.start)
        self.assertEqual(961072245, arguments.end)

    def test_parseArguments_whenDatetimeSetWithEqual(self) -> None:
        arguments = parse_arguments(["--datetime=2000-06-15 12:30:45"])
        self.assertEqual(961072245, arguments.start)
        self.assertEqual(961072245, arguments.end)

    def test_parseArguments_whenStartAsDatetimeISO(self) -> None:
        arguments = parse_arguments(["--start", "2000-06-15T12:30:45Z"])
        self.assertEqual(961072245, arguments.start)
        self.assertEqual(961072245, arguments.end)

    def test_parseArguments_whenStartAsDatetimeAmbiguous(self) -> None:
        arguments = parse_arguments(["--start", "2000-06-15 12:30:45"])
        self.assertEqual(961072245, arguments.start)
        self.assertEqual(961072245, arguments.end)

    def test_parseArguments_whenStartAsDatetimeSetWithEqual(self) -> None:
        arguments = parse_arguments(["--start=2000-06-15 12:30:45"])
        self.assertEqual(961072245, arguments.start)
        self.assertEqual(961072245, arguments.end)

    def test_parseArguments_whenEndAsDatetimeISO(self) -> None:
        arguments = parse_arguments(
            ["--start", "2000-06-15T12:30:45Z", "--end", "2000-06-15T13:30:45Z"]
        )
        self.assertEqual(961072245, arguments.start)
        self.assertEqual(961075845, arguments.end)

    def test_parseArguments_whenEndAsDatetimeAmbiguous(self) -> None:
        arguments = parse_arguments(
            ["--start", "2000-06-15 12:30:45", "--end", "2000-06-15 13:30:45"]
        )
        self.assertEqual(961072245, arguments.start)
        self.assertEqual(961075845, arguments.end)

    def test_parseArguments_whenEndAsDatetimeSetWithEqual(self) -> None:
        arguments = parse_arguments(["--start=2000-06-15 12:30:45", "--end=2000-06-15 13:30:45"])
        self.assertEqual(961072245, arguments.start)
        self.assertEqual(961075845, arguments.end)

    def test_parseArguments_whenOnlyWrongZone(self) -> None:
        with self.assertRaises(argparse.ArgumentError) as cm:
            parse_arguments(["--timestamp", "961072245", "--zone", "FRANCE"], exit_on_error=False)
        self.assertEqual(
            "argument --zone: invalid choice: 'FRANCE' (choose from 'METROPOLE', 'ANTILLES', 'REUNION')",
            str(cm.exception),
        )

    def test_parseArguments_whenOneWrongZone(self) -> None:
        with self.assertRaises(argparse.ArgumentError) as cm:
            parse_arguments(
                ["--timestamp", "961072245", "--zone", "METROPOLE", "--zone", "FRANCE"],
                exit_on_error=False,
            )
        self.assertEqual(
            "argument --zone: invalid choice: 'FRANCE' (choose from 'METROPOLE', 'ANTILLES', 'REUNION')",
            str(cm.exception),
        )

    def test_parseArguments_whenTwoWrongZone(self) -> None:
        with self.assertRaises(argparse.ArgumentError) as cm:
            parse_arguments(
                ["--timestamp", "961072245", "--zone", "FRANCE", "--zone", "ESPAGNE"],
                exit_on_error=False,
            )
        self.assertEqual(
            "argument --zone: invalid choice: 'FRANCE' (choose from 'METROPOLE', 'ANTILLES', 'REUNION')",
            str(cm.exception),
        )

    def test_parseArguments_whenOnlyWrongZones(self) -> None:
        with self.assertRaises(argparse.ArgumentError) as cm:
            parse_arguments(["--timestamp", "961072245", "--zones", "FRANCE"], exit_on_error=False)
        self.assertEqual(
            "argument --zones: invalid choice: 'FRANCE' (choose from 'METROPOLE', 'ANTILLES', 'REUNION')",
            str(cm.exception),
        )

    def test_parseArguments_whenOneWrongZones(self) -> None:
        with self.assertRaises(argparse.ArgumentError) as cm:
            parse_arguments(
                ["--timestamp", "961072245", "--zones", "METROPOLE", "FRANCE"],
                exit_on_error=False,
            )
        self.assertEqual(
            "argument --zones: invalid choice: 'FRANCE' (choose from 'METROPOLE', 'ANTILLES', 'REUNION')",
            str(cm.exception),
        )

    def test_parseArguments_whenTwoWrongZones(self) -> None:
        with self.assertRaises(argparse.ArgumentError) as cm:
            parse_arguments(
                ["--timestamp", "961072245", "--zones", "FRANCE", "ESPAGNE"],
                exit_on_error=False,
            )
        self.assertEqual(
            "argument --zones: invalid choice: 'FRANCE' (choose from 'METROPOLE', 'ANTILLES', 'REUNION')",
            str(cm.exception),
        )

    def test_parseArguments_whenNoZone(self) -> None:
        arguments = parse_arguments(["--timestamp", "961072245"])
        self.assertEqual([Zone(zone) for zone in ZONES], arguments.zones)

    def test_parseArguments_whenZone(self) -> None:
        arguments = parse_arguments(["--timestamp", "961072245", "--zone", "METROPOLE"])
        self.assertEqual([Zone.METROPOLE], arguments.zones)

    def test_parseArguments_whenZoneZone(self) -> None:
        arguments = parse_arguments(
            ["--timestamp", "961072245", "--zone", "METROPOLE", "--zone", "REUNION"]
        )
        self.assertEqual([Zone.METROPOLE, Zone.REUNION], arguments.zones)

    def test_parseArguments_whenOneZones(self) -> None:
        arguments = parse_arguments(["--timestamp", "961072245", "--zones", "METROPOLE"])
        self.assertEqual([Zone.METROPOLE], arguments.zones)

    def test_parseArguments_whenTwoZones(self) -> None:
        arguments = parse_arguments(["--timestamp", "961072245", "--zones", "METROPOLE", "REUNION"])
        self.assertEqual([Zone.METROPOLE, Zone.REUNION], arguments.zones)

    def test_parseArguments_whenEmptyZone(self) -> None:
        with self.assertRaises(argparse.ArgumentError) as cm:
            parse_arguments(["--timestamp", "961072245", "--zone"], exit_on_error=False)
        self.assertEqual(
            "argument --zone: expected one argument",
            str(cm.exception),
        )

    def test_parseArguments_whenEmptyZones(self) -> None:
        with self.assertRaises(argparse.ArgumentError) as cm:
            parse_arguments(["--timestamp", "961072245", "--zones"], exit_on_error=False)
        self.assertEqual(
            "argument --zones: expected at least one argument",
            str(cm.exception),
        )

    def test_parseArguments_whenNoReplace(self) -> None:
        arguments = parse_arguments(["--timestamp", "961072245"])
        self.assertFalse(arguments.replace)

    def test_parseArguments_whenReplace(self) -> None:
        arguments = parse_arguments(["--timestamp", "961072245", "--replace"])
        self.assertTrue(arguments.replace)


if __name__ == "__main__":
    unittest.main()
