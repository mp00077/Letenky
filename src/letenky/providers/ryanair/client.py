import json
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from letenky.domain.errors import InvalidResponse, ProviderError


class RyanairClient:
    BASE = "https://www.ryanair.com"

    def get(self, path: str, params: dict | None = None):
        url = self.BASE + path + ("?" + urlencode(params) if params else "")
        request = Request(url, headers={"Accept": "application/json",
                                       "User-Agent": "Letenky/0.1 (desktop price monitor)"})
        for attempt in range(2):
            try:
                with urlopen(request, timeout=20) as response:
                    body = response.read(5_000_001)
                if len(body) > 5_000_000:
                    raise InvalidResponse("Odpověď Ryanairu překročila povolenou velikost.")
                return json.loads(body)
            except HTTPError as exc:
                if exc.code in {500, 502, 503, 504} and attempt == 0:
                    time.sleep(1)
                    continue
                if exc.code in {403, 409, 429}:
                    raise ProviderError(f"Ryanair omezil přístup (HTTP {exc.code}). Zkuste kontrolu později.") from exc
                raise ProviderError(f"Ryanair vrátil HTTP {exc.code}.") from exc
            except (URLError, TimeoutError, socket.timeout, OSError) as exc:
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise ProviderError("Ryanair není dostupný. Ověřte připojení k internetu.") from exc
            except (ValueError, UnicodeError) as exc:
                raise InvalidResponse("Ryanair nevrátil platná data JSON.") from exc
