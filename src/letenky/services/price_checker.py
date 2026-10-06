import logging
from threading import Lock

from letenky.domain.price import utc_now

log = logging.getLogger(__name__)


class PriceChecker:
    def __init__(self, provider, repository, clock=utc_now):
        self.provider = provider
        self.repository = repository
        self.clock = clock
        self._lock = Lock()
        self._running = set()

    def check(self, watch_id):
        with self._lock:
            if watch_id in self._running:
                return False
            self._running.add(watch_id)
        try:
            self.repository.expire(self.clock())
            watch = self.repository.get(watch_id)
            if watch is None or watch.state != "active":
                return False
            started = self.clock()
            alternative = None
            try:
                offers = self.provider.search(watch.query)
                matches = [offer for offer in offers if offer.matches(watch.query)
                           and offer.flight_number == watch.flight_number]
                if len(matches) > 1:
                    raise ValueError("Zdroj vrátil nejednoznačnou nabídku stejného letu.")
                offer = matches[0] if matches else None
                status, error = ("ok", None) if offer else ("not_offered", None)
                if offer is None:
                    candidates = [item for item in offers if item.matches(watch.query)
                                  and item.source == "ryanair_farefinder"
                                  and item.flight_number != watch.flight_number
                                  and item.departure > self.clock()]
                    alternative = min(candidates, key=lambda item: (item.amount_minor, item.departure,
                                                                  item.flight_number), default=None)
            except Exception as exc:
                log.exception("Kontrola sledování %s selhala", watch_id)
                offer, status, error, alternative = None, "error", str(exc), None
            finished = self.clock()
            if alternative is not None and alternative.departure <= finished:
                alternative = None
            return self.repository.record_check(watch, started, finished, status, error, offer,
                                                alternative=alternative)
        finally:
            with self._lock:
                self._running.discard(watch_id)
