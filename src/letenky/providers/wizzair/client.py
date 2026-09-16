import json
import os
import re
import ssl
from http.cookiejar import CookieJar
from threading import RLock
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, HTTPCookieProcessor, Request, build_opener

from letenky.domain.errors import InvalidResponse, ProviderError
from letenky.infrastructure.tls import create_tls_context


class WizzairClient:
    HOME = "https://www.wizzair.com/en-gb"

    def __init__(self):
        self._lock = RLock()
        self._opener = None
        self._cookies = CookieJar()
        self._base = None
        self._ready_at = None

    def _token(self):
        # Session tokens are only sent back to the airline's own API.
        return next((cookie.value for cookie in self._cookies
                     if cookie.name == "RequestVerificationToken" and not cookie.is_expired()
                     and cookie.domain.lstrip(".") in {"wizzair.com", "be.wizzair.com"}), None)

    def _request(self, url, payload=None, *, html=False):
        headers = {"User-Agent": "Letenky/0.1 (desktop price monitor)",
                   "Accept": "text/html" if html else "application/json",
                   "Origin": "https://www.wizzair.com", "Referer": self.HOME}
        if not html and (token := self._token()):
            headers["X-RequestVerificationToken"] = token
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        try:
            with self._opener.open(Request(url, data=data, headers=headers), timeout=20) as response:
                body = response.read(5_000_001)
            if len(body) > 5_000_000:
                raise InvalidResponse("Odpověď Wizz Air překročila povolenou velikost.")
            if html:
                return body.decode("utf-8")
            result = json.loads(body)
            if not isinstance(result, dict):
                raise InvalidResponse("Wizz Air vrátil neočekávaný formát odpovědi.")
            if result.get("handlerError") or result.get("validationCodes"):
                self._ready_at = None
                raise ProviderError("Wizz Air odmítl dotaz nebo platnost relace. Zkuste kontrolu později.")
            return result
        except HTTPError as exc:
            code = exc.code
            exc.close()
            if code in {400, 401, 403, 404, 405, 409, 428, 429}:
                self._ready_at = None
            if code in {403, 405, 409, 428, 429}:
                raise ProviderError(f"Wizz Air omezuje automatický přístup nebo vyžaduje ověření návštěvníka (HTTP {code}). Cena nebyla získána.") from exc
            if code == 404:
                raise ProviderError("Cenové rozhraní Wizz Air není dostupné nebo se změnila jeho verze (HTTP 404).") from exc
            raise ProviderError(f"Wizz Air odmítl požadavek (HTTP {code}). Cena nebyla získána.") from exc
        except (URLError, OSError) as exc:
            reason = exc.reason if isinstance(exc, URLError) else exc
            if isinstance(reason, ssl.SSLCertVerificationError):
                message = "Nelze ověřit HTTPS certifikát Wizz Air. Zkontrolujte datum počítače, certifikáty a případnou proxy."
            elif isinstance(reason, TimeoutError):
                message = "Spojení s Wizz Air překročilo časový limit."
            else:
                message = "Nepodařilo se připojit k Wizz Air. Technický detail je v letenky.log."
            raise ProviderError(message) from exc
        except (ValueError, UnicodeError) as exc:
            raise InvalidResponse("Wizz Air nevrátil očekávaná data. Může vyžadovat ověření návštěvníka.") from exc

    def _prepare_session(self):
        if self._ready_at is not None and monotonic() - self._ready_at < 3600:
            return
        self._ready_at = None
        self._cookies.clear()
        try:
            self._opener = build_opener(HTTPCookieProcessor(self._cookies), HTTPSHandler(context=create_tls_context()))
        except (OSError, ValueError) as exc:
            raise ProviderError("Nelze načíst HTTPS certifikáty pro Wizz Air. Ověřte instalaci certifi.") from exc
        version = os.environ.get("WIZZAIR_API_VERSION", "").strip()
        if version:
            if not re.fullmatch(r"\d+\.\d+\.\d+", version):
                raise ProviderError("WIZZAIR_API_VERSION musí mít formát například 29.14.0.")
            self._base = f"https://be.wizzair.com/{version}/Api"
        else:
            html = self._request(self.HOME, html=True).replace("\\/", "/")
            match = re.search(r'https://be\.wizzair\.com/\d+\.\d+\.\d+/Api(?=["\s\x27<])', html)
            if not match:
                raise ProviderError("Z webu Wizz Air nelze zjistit aktuální cenové rozhraní. Web mohl změnit formát nebo vyžaduje ověření návštěvníka.")
            self._base = match.group(0)
        self._request(self._base + "/userSession/new")
        if self._token() is None:
            raise ProviderError("Wizz Air neposkytl platnou anonymní relaci. Cena nebyla získána.")
        self._ready_at = monotonic()

    def timetable(self, query):
        # The anonymous session's verification cookie can rotate on any response.
        # Serialize this provider's requests and read the cookie before each one.
        with self._lock:
            self._prepare_session()
            return self._request(self._base + "/search/timetableV2", {
                "flightList": [{"departureStation": query.origin, "arrivalStation": query.destination,
                                "from": query.departure_date.isoformat(), "to": query.departure_date.isoformat()}],
                "priceType": "regular", "adultCount": 1, "childCount": 0, "infantCount": 0,
            })
