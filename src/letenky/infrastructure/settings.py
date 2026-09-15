import json
import logging
from dataclasses import asdict, dataclass


@dataclass
class Settings:
    currency: str = "CZK"
    close_to_tray: bool = True

    @classmethod
    def load(cls, directory):
        try:
            data = json.loads((directory / "settings.json").read_text(encoding="utf-8"))
            currency = data.get("currency", "CZK")
            tray = data.get("close_to_tray", True)
            return cls(currency if currency in {"CZK", "EUR", "GBP", "PLN"} else "CZK",
                       tray if isinstance(tray, bool) else True)
        except FileNotFoundError:
            return cls()
        except (ValueError, OSError, AttributeError):
            logging.getLogger(__name__).warning("Nastavení nelze načíst; použity výchozí hodnoty.")
            return cls()

    def save(self, directory):
        temp = directory / "settings.json.tmp"
        temp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        temp.replace(directory / "settings.json")
