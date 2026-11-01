# E-commerce Feed Converter

**Plik z hurtowni → gotowy import do sklepu + raport jakości danych.**

Hurtownie wysyłają cenniki w każdym możliwym formacie: ceny raz z przecinkiem, raz z „zł”,
EAN-y zepsute przez Excela, duplikaty, nazwy pisane CAPS LOCKIEM, zdjęcia jako same nazwy plików.
To narzędzie zamienia taki plik na **czysty import do WooCommerce lub Shopera** i tworzy
**raport w Excelu**, który mówi klientowi dokładnie, czego brakuje i w którym wierszu.

## Efekt na przykładowym pliku (413 wierszy)

| | |
|---|---|
| Gotowych do importu | **350** produktów |
| Odrzuconych z podaniem powodu | **63** (zły EAN, brak ceny, duplikaty) |
| Ostrzeżenia (nie blokują importu) | brak opisu → opis z danych, brak zdjęć, stan „dostępny” |
| Czas przetwarzania | < 2 s |

## Co robi

- **Rozpoznaje kolumny** niezależnie od nazewnictwa hurtowni (`Kod EAN`, `EAN13`, `Kod kreskowy` → `ean`).
- **Waliduje EAN/GTIN**: cyfra kontrolna, długość, duplikaty, przywraca zera wiodące zgubione przez Excela,
  wykrywa EAN-y zniszczone notacją naukową (`5,90123E+12`).
- **Normalizuje ceny i VAT**: `1 299,00 PLN`, `12.99 zł`, `23%`, `0.23`; liczy brutto z netto (lub odwrotnie)
  na typie `Decimal`, bez błędów zaokrągleń.
- **Porządkuje treści**: nazwy (spacje, CAPS LOCK, jednostki), kategorie (`dom/kuchnia` → `Dom > Kuchnia`),
  opisy HTML (usuwa style, skrypty i śmieciowe tagi).
- **Opis z danych, nie z wyobraźni**: gdy hurtownia nie podała opisu, tworzy go wyłącznie z pól z pliku
  (producent, kolor, waga). Nie dopisuje parametrów, których nie ma w danych.
- **Eksportuje** do natywnego importera WooCommerce oraz do CSV dla Shopera.
- **Raport dla klienta** (`raport_jakosci_danych.xlsx`): podsumowanie, lista odrzuconych z powodem,
  wszystkie problemy z numerem wiersza, podgląd importu.

## Uruchomienie

```bash
pip install -r requirements.txt
python generate_sample.py                     # tworzy przykładowy "brudny" plik
python convert.py sample_data/hurtownia_feed.xlsx --platform woocommerce shoper
```

Opcje:

| Opcja | Opis |
|---|---|
| `--platform woocommerce shoper` | docelowe formaty importu |
| `--image-base-url https://cdn.sklep.pl/foto` | adres serwera dla zdjęć podanych jako nazwy plików |
| `--default-vat 0.23` | stawka VAT, gdy w pliku jej brak |
| `--net-prices` | WooCommerce: ceny netto zamiast brutto |
| `--out wynik` | folder wynikowy (domyślnie `output/`) |

Wynik w `output/`:

```
import_woocommerce.csv      # Produkty → Import w WooCommerce
import_shoper.csv           # import CSV w Shoperze
raport_jakosci_danych.xlsx  # raport dla klienta
```

> **Shoper:** nagłówki pliku dopasowuje się do szablonu importu pobranego z panelu danego sklepu.
> Mapowanie jest w jednym słowniku, `SHOPER_COLUMNS` w `feedconv/export.py`.

## Struktura

```
convert.py            # CLI
generate_sample.py    # generator danych testowych z typowymi błędami
feedconv/
  columns.py          # rozpoznawanie nagłówków
  clean.py            # czyszczenie wartości (EAN, ceny, VAT, HTML, nazwy)
  pipeline.py         # walidacja wierszy, duplikaty, błędy i ostrzeżenia
  export.py           # formaty WooCommerce / Shoper
  report.py           # raport Excel
tests/                # testy jednostkowe (pytest)
```

```bash
python -m pytest -q
```

## Możliwe rozszerzenia

- Wysyłka bezpośrednio przez API (WooCommerce REST, Shoper REST, BaseLinker `addInventoryProduct`).
- Uzupełnianie parametrów po EAN z katalogu produktów Allegro.
- Opisy SEO generowane przez LLM, ograniczone do faktów z pliku (structured output + walidacja).

Dane w `sample_data/` są w całości fikcyjne.
