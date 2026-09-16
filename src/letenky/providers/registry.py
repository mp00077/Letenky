from letenky.domain.carrier import CARRIERS
from letenky.domain.errors import ProviderError


class ProviderRegistry:
    def __init__(self, providers):
        self.providers = providers

    def carriers(self):
        return [(key, CARRIERS[key]) for key in self.providers]

    def get(self, carrier):
        try:
            return self.providers[carrier]
        except KeyError as exc:
            raise ProviderError("Pro vybraného dopravce není dostupný zdroj cen.") from exc

    def airports(self, carrier="ryanair"):
        return self.get(carrier).airports()

    def search(self, query):
        return self.get(query.carrier).search(query)


def as_registry(provider):
    return provider if isinstance(provider, ProviderRegistry) else ProviderRegistry({"ryanair": provider})


def default_providers():
    from .ryanair.provider import RyanairProvider
    from .wizzair.provider import WizzairProvider
    return ProviderRegistry({"ryanair": RyanairProvider(), "wizzair": WizzairProvider()})
