from datetime import datetime, time, timedelta

CARRIERS = {"ryanair": "Ryanair", "wizzair": "Wizz Air"}
SOURCE_CARRIERS = {"ryanair_farefinder": "ryanair", "wizzair_timetable": "wizzair"}


def carrier_for_source(source):
    try:
        return SOURCE_CARRIERS[source]
    except KeyError as exc:
        raise ValueError(f"Nepodporovaný zdroj cen: {source}") from exc


def is_daily_minimum(source):
    return source == "wizzair_timetable"


def tracking_deadline(departure, source):
    if is_daily_minimum(source):
        return datetime.combine(departure.date() + timedelta(days=1), time.min, departure.tzinfo)
    return departure
