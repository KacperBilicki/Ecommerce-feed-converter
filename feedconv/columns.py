"""Rozpoznawanie kolumn: każda hurtownia nazywa je inaczej."""
import re
import unicodedata

# pole kanoniczne -> znormalizowane nagłówki, pod którymi występuje w plikach hurtowni
ALIASES = {
    "ean": ["ean", "kod ean", "ean13", "kod kreskowy", "gtin", "barcode"],
    "sku": ["sku", "symbol", "kod produktu", "kod towaru", "indeks", "index"],
    "name": ["nazwa", "nazwa towaru", "nazwa produktu", "name", "tytul"],
    "price_net": ["cena netto", "netto", "cena hurtowa netto", "price net"],
    "price_gross": ["cena brutto", "brutto", "cena detaliczna", "cena", "price"],
    "vat": ["vat", "stawka vat", "podatek vat"],
    "stock": ["stan", "stan mag", "stan magazynowy", "ilosc", "stock", "dostepnosc"],
    "category": ["kategoria", "kategorie", "category", "grupa towarowa"],
    "brand": ["producent", "marka", "brand", "manufacturer"],
    "description": ["opis", "opis produktu", "description"],
    "weight": ["waga", "masa", "weight"],
    "color": ["kolor", "color", "barwa"],
}
IMAGE_HEADER = re.compile(r"^(zdjecie|zdjecia|foto|image|images|img|obraz)( \d+)?$")


def normalize_header(header) -> str:
    """'Cena netto [PLN]' -> 'cena netto', 'Stan mag.' -> 'stan mag'."""
    text = str(header).lower().replace("ł", "l")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"\[.*?\]|\(.*?\)", " ", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def map_columns(columns) -> tuple[dict[str, str], list[str], list[str]]:
    """Zwraca (kolumna źródłowa -> pole, kolumny ze zdjęciami, kolumny pominięte)."""
    lookup = {alias: field for field, aliases in ALIASES.items() for alias in aliases}
    mapping, images, unmapped = {}, [], []
    for col in columns:
        key = normalize_header(col)
        field = lookup.get(key)
        if field and field not in mapping.values():
            mapping[col] = field
        elif IMAGE_HEADER.match(key):
            images.append(col)
        else:
            unmapped.append(col)
    return mapping, images, unmapped
