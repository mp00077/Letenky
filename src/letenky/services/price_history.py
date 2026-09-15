from letenky.domain.price import local_time, money

STATUS_LABELS = {"ok": "Cena zjištěna", "not_offered": "Let není v nabídce zdroje", "error": "Chyba kontroly"}


def price_summary(watch):
    latest = money(watch.latest_amount, watch.currency)
    if watch.minimum_amount is None:
        return latest
    minimum_date = local_time(watch.minimum_at).rsplit(" ", 1)[0]
    return f"{latest} (min. {money(watch.minimum_amount, watch.currency)} dne {minimum_date})"
