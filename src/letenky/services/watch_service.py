from datetime import timedelta

from letenky.domain.price import utc_now


class WatchService:
    def __init__(self, repository):
        self.repository = repository

    def add(self, offer):
        now = utc_now()
        if offer.departure <= now:
            raise ValueError("Tento let již odletěl.")
        if now - offer.observed_at > timedelta(minutes=15):
            raise ValueError("Výsledek hledání je starší než 15 minut. Vyhledejte let znovu.")
        return self.repository.add(offer)

    def delete(self, watch_id):
        return self.repository.delete(watch_id)
