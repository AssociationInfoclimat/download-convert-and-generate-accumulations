from argparse import ArgumentParser
from typing import Optional

from .datetime_utils import timestamp_of
from .tiles import Zone

ZONES = [
    Zone.METROPOLE.value,
    Zone.ANTILLES.value,
    Zone.REUNION.value,
    # Zone.NOUVELLE_CALEDONIE.value,
]


class Arguments:
    def __init__(
        self,
        start: int,
        end: int,
        zones: Optional[list[str]] = None,
        replace: bool = False,
    ) -> None:
        self.start = start
        self.end = end
        self.zones = [Zone(zone) for zone in (zones or ZONES)]
        self.replace = replace


def timestamp_of_argument(value: str) -> int:
    """if timestamp, return timestamp, if iso date string, return timestamp of date"""
    if value.isdigit():
        return int(value)
    return timestamp_of(value)


def parse_arguments(arguments: list[str], *, exit_on_error: bool = True) -> Arguments:
    argument_parser = ArgumentParser(exit_on_error=exit_on_error)
    timestamp_group = argument_parser.add_mutually_exclusive_group(required=True)
    timestamp_group.add_argument(
        "--timestamp",
        type=int,
        action="store",
        dest="start",
        help="set start and end to the same datetime",
    )
    timestamp_group.add_argument(
        "--datetime",
        type=timestamp_of,
        action="store",
        dest="start",
        help="set start and end to the same datetime",
    )
    timestamp_group.add_argument(
        "--start",
        type=timestamp_of_argument,
        action="store",
        dest="start",
    )
    argument_parser.add_argument(
        "--end",
        type=timestamp_of_argument,
        action="store",
        help="(inclusive) if not given, end is set to start",
    )
    argument_parser.add_argument(
        "--zone",
        type=str,
        required=False,
        action="append",
        dest="zones",
        default=[],
        choices=ZONES,
    )
    argument_parser.add_argument(
        "--zones",
        type=str,
        required=False,
        action="extend",
        nargs="+",
        dest="zones",
        default=[],
        choices=ZONES,
    )
    argument_parser.add_argument(
        "--replace",
        required=False,
        action="store_true",
        default=False,
    )
    parsed = argument_parser.parse_args(arguments)
    return Arguments(
        start=parsed.start,
        end=parsed.end if parsed.end else parsed.start,
        zones=parsed.zones,
        replace=parsed.replace,
    )
