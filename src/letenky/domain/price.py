from datetime import datetime, timezone


def currency_decimals(currency):
    if currency in {"BHD", "IQD", "JOD", "KWD", "LYD", "OMR", "TND"}:
        return 3
    if currency in {"BIF", "CLP", "DJF", "GNF", "ISK", "JPY", "KMF", "KRW", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}:
        return 0
    return 2


def currency_factor(currency):
    return 10 ** currency_decimals(currency)


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
    units, cents = divmod(amount, currency_factor(currency))
    decimals = currency_decimals(currency)
    number = f"{units:,}".replace(",", " ") + (f",{cents:0{decimals}d}" if cents else "")
    return f"{number} { {'CZK': 'Kč'}.get(currency, currency)}"
