# Přehled změn

Nové změny zapisujeme pod aktuální datum, nejnovější záznamy jsou nahoře.

## 2026-09-17

- V hlavním seznamu sledovaných letů přidáno zelené označení a šipka dolů při poklesu ceny, červené označení a šipka nahoru při růstu. Porovnávají se poslední dvě získané ceny; nezměněná cena je neutrální a tooltip uvádí rozdíl.

## 2026-09-16

- Přidáno smazání vybraného sledování včetně historie cen s potvrzením v aplikaci.
- Přidán společný interval kontrol v Nastavení: 1 až 10 080 minut, výchozí 180 minut. Změna přepočítá termíny aktivních sledování a zachová se po restartu i pro kontrolu bez oken.
- Doplněna migrace databáze a ochrana před uložením opožděného výsledku ke smazanému nebo nově založenému sledování.
- Doplněny HTTPS certifikáty `certifi` a samostatná hlášení chyb certifikátu, DNS, timeoutu a odmítnutého spojení.
- Opraveno zkracování čísel v kalendáři data odletu způsobené společným stylem tabulek.
- Přidána kontrola spuštěné Windows aplikace před přepisem distribuční složky při buildu.
- Založen tento soubor pro průběžné zaznamenávání změn.

## 2026-09-15

- Vytvořena první verze aplikace v PySide6: vyhledávání nabídek Ryanairu, ukládání sledování, historie cen, minimum s datem a graf.
- Přidány pravidelné kontroly, pozastavení, běh v systémové liště a kontrola bez oken.
- Připraveno generování UI, lazy importy, bootstrap a nativní buildy pro Windows, macOS a Linux; ověřen Windows build.
