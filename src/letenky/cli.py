import json


def check_due(database):
    from letenky.providers.ryanair.provider import RyanairProvider
    from letenky.scheduling.runner import run_due
    from letenky.services.price_checker import PriceChecker
    from letenky.storage.repositories.watches import WatchRepository
    repository = WatchRepository(database)
    run_due(repository, PriceChecker(RyanairProvider(), repository))
    watches = repository.list()
    print(json.dumps([{"id": w.id, "state": w.state, "status": w.last_status,
                       "amount_minor": w.latest_amount, "currency": w.currency,
                       "observed_at": w.latest_at, "error": w.last_error}
                      for w in watches], ensure_ascii=True, indent=2))
    return int(any(w.last_status == "error" and w.state == "active" for w in watches))
