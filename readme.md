# JufDea naamkaartjes v2026

Een kleine NiceGUI-app om gepersonaliseerde naamkaartjes en een groepslijst als
PDF te maken.

## Starten

Installeer [uv](https://docs.astral.sh/uv/) en voer daarna uit:

```shell
uv sync
uv run python app.py
```

Open vervolgens <http://localhost:8080>. Elke browser-tab heeft een eigen lijst
met leerlingen. De knop **PDF downloaden** maakt één liggende pagina per
leerling en voegt achteraan de groepslijst toe.

## Statische website

Dezelfde app kan volledig in de browser draaien met Pyodide. Er worden geen
leerlinggegevens naar een server gestuurd.

```shell
./scripts/build-static.sh
python -m http.server -d dist/client 8080
```

Open vervolgens <http://localhost:8080>. De eerste start duurt langer omdat de
browser Python en de PDF-bibliotheken moet laden. Layout-instellingen worden in
de lokale browseropslag bewaard.

Een gedownloade PDF bevat ook de leerlingen en layout waarmee hij is gemaakt.
Gebruik **PDF openen** om zo'n bestand later opnieuw te bewerken. Oudere
JufDea-PDF's met `table.json`- en `layout.json`-bijlagen worden eveneens
ondersteund. Bij oudere JufDea-PDF's zonder bijlagen probeert de app de
leerlingen, groepen en afbeeldingen uit de pagina's te reconstrueren. Gewone
PDF's die de JufDea-layout niet volgen worden geweigerd.

## Werking

- `app.py` bevat uitsluitend de NiceGUI-pagina en interacties.
- `models.py` bevat de leerlinggegevens, afbeeldingencatalogus en validatie.
- `pdf_utils.py` rendert previews en volledige PDF's.
- `layout.json` bevat de bewerkbare afmetingen en posities.
- `GUI/images/ontwerpen` en `GUI/assets` bevatten de PDF-assets.

De layout kan vanuit de app via **Instellingen** als JSON worden aangepast. De
preview gebruikt altijd de actieve layout. Tekstinvoer wordt kort gebundeld en
de preview wordt als afbeelding ververst, zodat de vorige preview zichtbaar
blijft tijdens het renderen.

## Ontwikkeling

```shell
uv run ruff check .
uv run pytest
```
