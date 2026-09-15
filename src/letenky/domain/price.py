from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Čas bez časového pásma nelze uložit.")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def local_time(value: str | None) -> str:
    return datetime.fromisoformat(value).astimezone().strftime("%d. %m. %Y %H:%M") if value else "—"


def money(amount: int | None, currency: str) -> str:
    if amount is None:
        return "—"
    units, cents = divmod(amount, 100)
    number = f"{units:,}".replace(",", " ") + (f",{cents:02d}" if cents else "")
    return f"{number} { {'CZK': 'Kč'}.get(currency, currency)}"
