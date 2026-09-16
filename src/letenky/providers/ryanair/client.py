import json
import socket
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from letenky.domain.errors import InvalidResponse, ProviderError
from letenky.infrastructure.tls import create_tls_context


def connection_error_message(reason) -> str:
    if isinstance(reason, ssl.SSLCertVerificationError):
        return ("Nelze ověřit HTTPS certifikát Ryanairu. Zkontrolujte datum a čas počítače "
                "a důvěryhodné certifikáty; spojení může ovlivňovat také proxy nebo VPN. "
                "Technický detail je v letenky.log.")
    if isinstance(reason, ssl.SSLError):
        return ("Nepodařilo se navázat zabezpečené spojení (TLS) s Ryanairem. "
                "Technický detail je v letenky.log.")
    if isinstance(reason, socket.gaierror):
        return ("Nelze zjistit síťovou adresu serveru Ryanairu (DNS). "
                "Ověřte připojení, nastavení DNS a případnou proxy nebo VPN.")
    if isinstance(reason, TimeoutError):
        return "Spojení s Ryanairem překročilo časový limit. Zkuste kontrolu později."
    if isinstance(reason, ConnectionRefusedError):
        return "Spojení bylo odmítnuto. Ověřte nastavení sítě, proxy a firewallu."
    return ("Nepodařilo se připojit k Ryanairu. Ověřte připojení, proxy nebo VPN. "
            "Technický detail je v letenky.log.")


class RyanairClient:
    BASE = "https://www.ryanair.com"

    def get(self, path: str, params: dict | None = None):
        url = self.BASE + path + ("?" + urlencode(params) if params else "")
        request = Request(url, headers={"Accept": "application/json",
                                       "User-Agent": "Letenky/0.1 (desktop price monitor)"})
        try:
            context = create_tls_context()
        except (OSError, ValueError) as exc:
            raise ProviderError("Nelze načíst důvěryhodné HTTPS certifikáty. "
                                "Ověřte instalaci aplikace a balíčku certifi. "
                                "Technický detail je v letenky.log.") from exc
        for attempt in range(2):
            try:
                with urlopen(request, timeout=20, context=context) as response:
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
                reason = exc.reason if isinstance(exc, URLError) else exc
                # A second identical attempt cannot repair an invalid certificate.
                if attempt == 0 and not isinstance(reason, ssl.SSLError):
                    time.sleep(1)
                    continue
                raise ProviderError(connection_error_message(reason)) from exc
            except (ValueError, UnicodeError) as exc:
                raise InvalidResponse("Ryanair nevrátil platná data JSON.") from exc
