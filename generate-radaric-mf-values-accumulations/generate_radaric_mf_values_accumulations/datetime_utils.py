import datetime
import json

ONE_MINUTE_IN_SECONDS = 60
FIVE_MINUTES_IN_SECONDS = 5 * ONE_MINUTE_IN_SECONDS
ONE_HOUR_IN_SECONDS = 60 * ONE_MINUTE_IN_SECONDS
ONE_DAY_IN_SECONDS = 24 * ONE_HOUR_IN_SECONDS


def get_timestamp_from_iso_utc_date(iso_utc_date: str) -> int:
    dt = datetime.datetime.fromisoformat(iso_utc_date.replace('Z', '+00:00'))
    dt = dt.replace(tzinfo=datetime.timezone.utc)
    return int(dt.timestamp())


def timestamp_of(iso_utc_date: str) -> int:
    return get_timestamp_from_iso_utc_date(iso_utc_date)


def get_datetime_from_timestamp(timestamp: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)


def datetime_of(timestamp: int) -> datetime.datetime:
    return get_datetime_from_timestamp(timestamp)


def to_iso(dt: datetime.datetime) -> str:
    return f"{dt:%Y-%m-%d}T{dt:%H:%M:%S}Z"


def timestamp_to_iso(timestamp: int) -> str:
    return to_iso(datetime_of(timestamp))


def get_date_object_for(timestamp: int) -> dict[str, str]:
    dt = get_datetime_from_timestamp(timestamp)
    return {
        "year": dt.year,
        "month": f"{dt.month:02d}",
        "day": f"{dt.day:02d}",
        "hour": f"{dt.hour:02d}",
        "minute": f"{dt.minute:02d}",
    }


def get_datetime_from_date_object(
    date_object: dict[str, str]
) -> datetime.datetime:
    year = int(date_object["year"])
    month = int(date_object["month"])
    day = int(date_object["day"])
    hour = int(date_object["hour"])
    minute = int(date_object["minute"])

    return datetime.datetime(
        year, month, day, hour, minute, tzinfo=datetime.timezone.utc
    )


def get_timestamp_from_json_date(donnees: str) -> int:
    date_object = json.loads(donnees)
    return int(get_datetime_from_date_object(date_object).timestamp())
