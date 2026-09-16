# Letenky

Desktopová aplikace v Pythonu a PySide6 pro sledování cen nabídek Ryanairu a denních minim Wizz Air.
České rozhraní, SQLite, nastavitelný interval kontrol (výchozí 3 hodiny), historie a graf ceny.

## Co první verze umí

- Výběr dopravce, odletového a příletového letiště z našeptávače, data a měny (u Wizz Air automaticky).
- Vyhledání nabídek a uložení vybraného konkrétního letu s první cenou.
- Jednosměrné lety, 1 dospělý, základní tarif; Ryanair CZK, EUR, GBP nebo PLN, Wizz Air měna odletového letiště.
- Automatické a ruční kontroly, pozastavení a obnovení sledování.
- Smazání vybraného sledování včetně historie cen po potvrzení. Probíhající kontrolu je nutné nejdříve nechat dokončit.
- Společný interval kontrol v Nastavení: 1 až 10 080 minut (7 dnů), výchozí 180 minut.
- Poslední zjištěná cena a historické minimum včetně data, čas poslední i další kontroly.
- Detail s grafem a historií úspěšných i neúspěšných kontrol.
- Běh v systémové liště, kde ji operační systém podporuje.
- Automatické ukončení sledování po odletu, u denního minima Wizz Air na konci zvoleného dne v místním čase odletového letiště; zachování historie.
- Jednorázová kontrola bez oken přes `--check-due`.
- Nativní build pro operační systém, na kterém se spustí build skript.

## Zdroj cen a jeho omezení

### Wizz Air — experimentální adaptér

V dialogu nového sledování vyberte Wizz Air. Adaptér používá cenový kalendář
`/search/timetableV2` a sleduje **nejnižší cenu za trasu a den**, nikoli konkrétní
číslo letu. Nejlevnější spoj se může mezi měřeními změnit. Čísla letů ani časy
příletu se nedoplňují odhadem. Cena se ukládá v měně vrácené zdrojem, bez přepočtu;
při změně měny se měření odmítne, aby se nesmíchala historie různých měn.
Historie, minimum s datem, graf, interval kontrol, pozastavení i smazání jsou společné
pro oba dopravce. Nabídky s alternativními letišti jsou odmítnuty jako nejednoznačné.

**Živé získání cen Wizz Air zatím nebylo ověřeno.** Při ověřování 16. 9. 2026 web
vyžadoval ověření návštěvníka (HTTP 405) a další rozhraní omezovalo automatický
přístup (HTTP 429). V tomto prostředí tedy nelze nové sledování Wizz Air založit,
dokud zdroj neposkytne skutečnou nabídku. Aplikace zobrazí chybu a nevytváří ceny.
Automatické testy používají syntetické odpovědi podle dokumentovaného formátu.

Aktuální verze API se zjišťuje z veřejné stránky, pak se vytvoří běžná anonymní
relace. Ochrany webu se neobcházejí. Pro diagnostiku lze zadat známou platnou verzi
proměnnou prostředí `WIZZAIR_API_VERSION` ve formátu `číslo.číslo.číslo`;
tato volba nezpřístupní blokované rozhraní. Katalog letišť obsahuje geografické
údaje, není potvrzením aktuálně provozovaných tras Wizz Air.
Podklad formátu: [dokumentace klienta Flywizz](https://github.com/victorlane/flywizz/blob/master/docs/internal-api-spec.md).

### Ryanair

Adaptér používá veřejný endpoint Ryanair Fare Finder:
`https://www.ryanair.com/api/farfnd/v4/oneWayFares`.
Živý test 15. 9. 2026 ověřil vyhledání PRG → STN dne 20. 11. 2026, let FR1014,
uložení ceny a další nezávislou kontrolu do dočasné databáze.

**Jde o orientační nabídky, nikoli úplný letový řád či garantovanou aktuální
rezervační cenu.** Zdroj může vrátit pouze vybranou nejlevnější nabídku. Prázdná
odpověď proto neprokazuje, že v daný den žádný let neexistuje. Pokud sledovaný let
zmizí z nabídky, aplikace uloží stav „Let není v nabídce zdroje“, zachová poslední
cenu a nepřiřadí mu cenu jiného letu. Čas měření a čas aktualizace ceny u zdroje
se ukládají odděleně. Konečnou cenu je nutné ověřit při rezervaci u Ryanairu.

Rezervační endpoint `/api/booking/v4/en-gb/availability` při ověření vrátil HTTP 409.
V této verzi se nepoužívá. Pokud bude dostupný spolehlivý zdroj úplné dostupnosti,
lze doplnit další implementaci `FlightProvider` bez změny obrazovek.
Přístup k veřejným endpointům se může změnit; chyby HTTP a změna formátu odpovědi
se zobrazí jako chyby kontroly, nikdy jako nulová cena nebo jistota neexistence letu.

Seznam letišť je přiložený snapshot veřejného seznamu Ryanairu z 15. 9. 2026
(`https://www.ryanair.com/api/views/locate/5/airports/en/active`). Aktualizace
snapshotu: `python scripts/update_airports.py`.

## Spuštění ze zdrojů

Python 3.11 nebo novější; doporučený jednotný build interpreter je Python 3.13.
Lokálně ověřeno také na Windows s Pythonem 3.14.7 a PySide6 6.10.2.

### Windows / PowerShell

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe scripts\run_dev.py
```

V tomto pracovním adresáři už je připravená `.venv` s Pythonem 3.14 a přístupem
k místně nainstalovanému PySide6/PyInstalleru. Lze spustit rovnou poslední příkaz.
Systémový příkaz `python` zde při ověření mířil na nefunkční Python Install Manager;
přímá cesta `.venv\Scripts\python.exe` jej obchází.

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python scripts/run_dev.py
```

`run_dev.py` před spuštěním vygeneruje Python moduly z `.ui` a `.qrc`.
Po vygenerování lze projekt volitelně nainstalovat editovatelně pomocí
`python -m pip install -e .` a spouštět `python -m letenky` či `letenky`.
Při změně formulářů je nutné generování zopakovat.

## Build

```powershell
.\.venv\Scripts\python.exe scripts\build.py
```

Na macOS/Linux použijte `.venv/bin/python scripts/build.py`.

Skript zavolá `pyside6-uic` a `pyside6-rcc` ze stejného prostředí jako aplikace,
spustí testy, provede build přes PyInstaller a offline ověří výsledný program
včetně načtení grafů. Generované soubory v `gui/generated` se ručně neupravují.
`packaging/letenky.spec` explicitně zahrnuje lazy moduly, Qt Charts, SVG, migrace,
letiště, časová pásma a certifikáty `certifi`. Výstup je typu one-folder; distribuujte celou složku.
Na Windows build používá omezený `PATH`, aby nepřibalil nekompatibilní ICU/SSL DLL
z jiných nástrojů (například Poppleru nebo Condy). Spouštějte jej přes `scripts/build.py`.

| Prostředí | Výstup |
|---|---|
| Windows | `dist/Letenky/Letenky.exe` a závislosti |
| macOS | `dist/Letenky.app` |
| Linux | `dist/Letenky/Letenky` a závislosti |

Nejde o cross-kompilaci. Každý systém a procesorová architektura potřebují vlastní
build. Pro Linux sestavujte na nejstarší cílové podporované distribuci kvůli glibc.
Podepisování, macOS notarizace a instalační balíčky nejsou v první verzi nastavené.
Workflow `.github/workflows/build.yml` připravuje samostatné buildy pro tři systémy;
jeho běh vyžaduje GitHub repozitář. Lokálně je ověřený Windows build; ostatní
platformy je nutné ověřit na příslušných systémech.

## Ukládání a plánování

- SQLite, logy a nastavení jsou v uživatelském adresáři získaném z `QStandardPaths`.
  Přesnou cestu ukazuje dialog Nastavení. Nezapisuje se vedle nainstalovaného programu.
- Adresář lze změnit přepínačem `--data-dir C:\cesta\data` (nebo POSIX cestou).
- Ceny se ukládají jako celá čísla nejmenších měnových jednotek, například haléřů.
- Časy kontrol se ukládají v UTC. GUI je převádí na místní čas počítače.
  Odlet/přílet se zobrazuje v místním čase daného letiště.
- Každé úspěšné měření vytváří záznam, i když se cena nezměnila.
- Cena, minimum a historie patří konkrétnímu letu, měně, zdroji a tarifu.
- Chyba či chybějící nabídka nemění poslední známou cenu. Graf v takovém místě
  přeruší spojnici; nezobrazuje odhad nulové ceny.
- Další kontrola je uložená v databázi. Po restartu nebo probuzení se zmeškaná
  kontrola provede jednou; minulá měření se nevymýšlejí.
- Vlastní interval se ukládá do stejné databáze, takže jej používá GUI i `--check-due`.
  Změna intervalu přepočítá aktivní sledování od poslední dokončené kontroly;
  pokud nový termín již uplynul, kontrola se provede při nejbližším průchodu plánovače.
  Pozastavená a ukončená sledování se neobnovují. Běžící kontrola použije při dokončení
  nový interval. Plánovač kontroluje splatné dotazy každých 30 sekund.
- Smazání odstraní sledování, jeho měření a záznamy kontrol v jediné transakci.
  Ostatní sledování stejného letu (například v jiné měně) zůstanou zachována.
- Po dočasné síťové chybě proběhne nejvýše jeden opakovaný HTTP pokus. HTTP 403,
  409 a 429 se okamžitě hlásí jako omezení přístupu, další kontrola je podle nastaveného intervalu.
- Síťová komunikace používá dva workery. Callbacky mění GUI pouze v hlavním vlákně.
- `QLockFile` brání dvěma instancím nad stejným datovým adresářem; v procesu se
  stejné sledování nemůže kontrolovat souběžně. Každá DB operace má vlastní spojení.
- Při ukončení se dokončí rozběhnuté operace a uloží výsledky.

Program musí běžet a počítač musí být zapnutý. Automatický start po přihlášení ani
systémová služba se samy neinstalují. Jednorázová kontrola pro případný systémový
plánovač se spouští takto (GUI se stejnou databází musí být ukončené):

```powershell
.\.venv\Scripts\python.exe scripts\run_dev.py --check-due
```

Při instalaci do prostředí lze použít `python -m letenky --check-due`. Výstup je JSON,
nenulový návratový kód signalizuje chybu. Pro použití CLI na Windows preferujte
Python spuštění; distribuované `.exe` je aplikace bez konzole.

## Vývoj a testy

Přehled datovaných změn je v [changelog.md](changelog.md). Po každé úpravě projektu
se doplňuje stručný záznam pod aktuální datum. Distribuční build se spouští pouze
na výslovný pokyn uživatele.

### Chyba připojení na macOS

Původní verze zobrazovala stejnou zprávu pro chybu certifikátu, DNS i timeout.
Samotná zpráva o připojení proto neznamená, že počítač nemá internet.
Aktuální zdroje tyto chyby rozlišují a pro HTTPS načítají také přenosnou sadu
důvěryhodných certifikátů z `certifi`. Ověřování certifikátu i názvu serveru zůstává zapnuté.
Konfigurace balení zahrnuje `certifi/cacert.pem`, aby příští balíček nezávisel
na umístění certifikátů na počítači, kde se sestavoval.

Při spuštění ze zdrojů aktualizujte závislosti ve stejném virtuálním prostředí:

```bash
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python scripts/run_dev.py
```

Instalace závislostí ani `run_dev.py` nevytváří distribuční build.
Již existující `.app` tyto změny automaticky nepřevezme.
Pro určení skutečné příčiny otevřete `letenky.log` v adresáři uvedeném v Nastavení
a vyhledejte chybu ze stejného času. Například `CERTIFICATE_VERIFY_FAILED`
znamená selhání ověření certifikátu, `gaierror` problém DNS a `timed out` timeout.
U Pythonu instalovaného z python.org může pomoci spuštění `Install Certificates.command`
v `/Applications/Python 3.x/` pro používanou verzi Pythonu; to se netýká automaticky
samostatně zabalené aplikace. Viz [dokumentace Pythonu pro macOS](https://docs.python.org/3/using/mac.html).

### Spuštění testů

```powershell
.\.venv\Scripts\python.exe scripts\generate_ui.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\visual_check.py
```

Testy nevolají síť. Vzorek odpovědi v `tests/fixtures/ryanair` pochází ze skutečného
veřejného požadavku. Testují peněžní částky, časová pásma, nekorektní odpovědi,
změnu letu, databázové transakce, minimum, výpadek zdroje, plánování po restartu,
souběh, pozastavení, expiraci a základní GUI včetně grafu a předávání mezi vlákny.
Vizuální test zapisuje pouze do `.test-data`; používá ilustrační historii cen.

### Ověření první verze (15. 9. 2026)

- 22 automatických testů prošlo.
- Živý průchod vyhledání → uložení → opakovaná kontrola prošel nad Ryanairem.
- Windows AMD64 build prošel offline testem startu a grafu i startem s nativním
  Windows Qt pluginem.
- Sestavené `.exe` úspěšně provedlo živou kontrolu přes HTTPS a uložilo druhé měření
  do dočasné SQLite databáze. Testovací záznamy nejsou součástí uživatelských dat.
- macOS a Linux jsou připravené v build skriptu a CI, jejich běh zde nebyl ověřen.

### Vrstvy

```text
gui → services → providers / storage
          ↑
     scheduling / cli
```

`domain` neimportuje Qt. `bootstrap` připraví prostředí, lock a databázi;
`application` propojí služby s GUI. Dialogy a Qt Charts se načítají až při použití.
SQL je v repository vrstvě, HTTP komunikace a parsování pouze v adaptéru Ryanairu.

### Dokumentace použitých nástrojů

- [pyside6-uic](https://doc.qt.io/qtforpython-6/tools/pyside-uic.html)
- [PyInstaller a nativní buildy](https://pyinstaller.org/en/stable/operating-mode.html)
- [Qt QThreadPool](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThreadPool.html)
