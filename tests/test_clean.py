from decimal import Decimal

import pytest

from feedconv import clean
from feedconv.columns import map_columns


@pytest.mark.parametrize("raw, expected", [
    (5901234123457, "5901234123457"),
    (5901234123457.0, "5901234123457"),
    ("590 1234 123457", "5901234123457"),
    ("590-1234-123457", "5901234123457"),
    (12345670, "12345670"),               # EAN-8
    (36000291452, "0036000291452"),       # UPC-A po utracie zera wiodącego
])
def test_clean_ean_valid(raw, expected):
    assert clean.clean_ean(raw) == (expected, None)


@pytest.mark.parametrize("raw, fragment", [
    (None, "brak"),
    ("", "brak"),
    (5901234123458, "cyfra kontrolna"),
    ("5,90123E+12", "notacja naukowa"),
    ("59012ABC23457", "niedozwolone"),
    (123456, "długość"),
])
def test_clean_ean_invalid(raw, fragment):
    code, problem = clean.clean_ean(raw)
    assert code is None and fragment in problem


@pytest.mark.parametrize("raw, expected", [
    (12.99, "12.99"), ("12,99", "12.99"), ("12.99 zł", "12.99"),
    ("1 299,00 PLN", "1299.00"), ("1.299,00", "1299.00"), ("1,299.00", "1299.00"), ("0", "0.00"),
])
def test_parse_price(raw, expected):
    assert clean.parse_price(raw) == Decimal(expected)


def test_parse_price_garbage():
    assert clean.parse_price(None) is None
    assert clean.parse_price("na zapytanie") is None


@pytest.mark.parametrize("raw, expected", [("23%", "0.23"), ("8 %", "0.08"), (23, "0.23"), (0.23, "0.23"), ("zw", "0")])
def test_parse_vat(raw, expected):
    assert clean.parse_vat(raw) == Decimal(expected)


@pytest.mark.parametrize("raw, expected", [(7, 7), ("brak", 0), (">10", 10), ("5 szt.", 5), ("dostępny", None)])
def test_parse_stock(raw, expected):
    assert clean.parse_stock(raw) == expected


def test_clean_name_caps_and_spaces():
    assert clean.clean_name("  WIERTARKA  UDAROWA 750W ") == "Wiertarka udarowa 750W"
    assert clean.clean_name("Patelnia  stalowa 28 cm") == "Patelnia stalowa 28 cm"
    assert clean.clean_name("WKRĘTARKA AKUMULATOROWA 18 V") == "Wkrętarka akumulatorowa 18 V"


@pytest.mark.parametrize("raw", ["dom/kuchnia", "Dom - Kuchnia", "Dom>Kuchnia", "dom | kuchnia"])
def test_normalize_category(raw):
    assert clean.normalize_category(raw) == "Dom > Kuchnia"


def test_collect_images():
    images, relative = clean.collect_images(["https://x.pl/a.jpg", "IMG_1.jpg", "https://x.pl/a.jpg"])
    assert images == ["https://x.pl/a.jpg"] and relative == ["IMG_1.jpg"]
    images, relative = clean.collect_images(["IMG_1.jpg"], base_url="https://cdn.pl/foto/")
    assert images == ["https://cdn.pl/foto/IMG_1.jpg"] and relative == []


def test_sanitize_html_strips_styles_and_scripts():
    dirty = '<div class="x"><span style="color:red">Tekst</span><script>alert(1)</script><br><br><b>Ok</b></div>'
    assert clean.sanitize_html(dirty) == "Tekst <br><b>Ok</b>"
    assert clean.sanitize_html("Zwykły opis & więcej") == "<p>Zwykły opis &amp; więcej</p>"


def test_build_description_uses_only_given_facts():
    short, long = clean.build_description("Konewka 5 l", "GardenPro", "", None)
    assert short == "Producent: GardenPro"
    assert "Kolor" not in long and "Waga" not in long


def test_map_columns():
    mapping, images, unmapped = map_columns(["Kod EAN", "Nazwa towaru", "Cena netto [PLN]", "Stan mag.",
                                            "Zdjęcie 1", "Zdjęcie 2", "Uwagi hurtowni"])
    assert mapping == {"Kod EAN": "ean", "Nazwa towaru": "name", "Cena netto [PLN]": "price_net",
                       "Stan mag.": "stock"}
    assert images == ["Zdjęcie 1", "Zdjęcie 2"] and unmapped == ["Uwagi hurtowni"]
