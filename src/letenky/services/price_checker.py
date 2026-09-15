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
            try:
                offers = self.provider.search(watch.query)
                matches = [offer for offer in offers if offer.matches(watch.query)
                           and offer.flight_number == watch.flight_number]
                if len(matches) > 1:
                    raise ValueError("Zdroj vrátil nejednoznačnou nabídku stejného letu.")
                offer = matches[0] if matches else None
                status, error = ("ok", None) if offer else ("not_offered", None)
            except Exception as exc:
                log.exception("Kontrola sledování %s selhala", watch_id)
                offer, status, error = None, "error", str(exc)
            self.repository.record_check(watch, started, self.clock(), status, error, offer)
            return True
        finally:
            with self._lock:
                self._running.discard(watch_id)
