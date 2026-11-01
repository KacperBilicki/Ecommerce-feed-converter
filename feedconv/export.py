"""Zapis plików importu dla konkretnych platform."""
import csv
from decimal import Decimal
from pathlib import Path

# Kolumny natywnego importera produktów WooCommerce (Produkty -> Import).
WOO_COLUMNS = [
    "Type", "SKU", "GTIN, UPC, EAN, or ISBN", "Name", "Published", "Short description", "Description",
    "Tax status", "Tax class", "In stock?", "Stock", "Regular price", "Categories", "Images", "Brands",
    "Weight (kg)", "Attribute 1 name", "Attribute 1 value(s)", "Attribute 1 visible", "Attribute 1 global",
]
WOO_TAX_CLASS = {Decimal("0.23"): "", Decimal("0.08"): "reduced-rate", Decimal("0.05"): "reduced-rate",
                 Decimal("0.00"): "zero-rate"}

# Shoper: nagłówki trzeba dopasować do szablonu pobranego z panelu sklepu
# (Asortyment -> Import / Eksport). Tu: kolumna w pliku -> pole produktu.
SHOPER_COLUMNS = {
    "kod_produktu": "sku",
    "ean": "ean",
    "nazwa": "name",
    "cena_brutto": "price_gross",
    "vat": "vat_percent",
    "stan": "stock",
    "kategoria": "category",
    "producent": "brand",
    "waga": "weight",
    "opis_krotki": "short_description",
    "opis": "description",
    "zdjecia": "images_joined",
}


def _fmt(value) -> str:
    return "" if value is None else str(value)


def to_woocommerce(products: list[dict], path: Path, *, prices_include_tax: bool = True) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=WOO_COLUMNS)
        writer.writeheader()
        for p in products:
            stock = p["stock"]
            writer.writerow({
                "Type": "simple",
                "SKU": p["sku"],
                "GTIN, UPC, EAN, or ISBN": p["ean"],
                "Name": p["name"],
                "Published": 1,
                "Short description": p["short_description"],
                "Description": p["description"],
                "Tax status": "taxable",
                "Tax class": WOO_TAX_CLASS.get(p["vat"], ""),
                "In stock?": "" if stock is None else int(stock > 0),
                "Stock": _fmt(stock),
                "Regular price": _fmt(p["price_gross"] if prices_include_tax else p["price_net"]),
                "Categories": p["category"],
                "Images": ", ".join(p["images"]),
                "Brands": p["brand"],
                "Weight (kg)": _fmt(p["weight"]),
                "Attribute 1 name": "Kolor" if p["color"] else "",
                "Attribute 1 value(s)": p["color"],
                "Attribute 1 visible": 1 if p["color"] else "",
                "Attribute 1 global": 0 if p["color"] else "",
            })


def to_shoper(products: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(SHOPER_COLUMNS.keys())
        for p in products:
            derived = {**p, "vat_percent": int(p["vat"] * 100), "images_joined": "|".join(p["images"])}
            writer.writerow(_fmt(derived[field]) for field in SHOPER_COLUMNS.values())


EXPORTERS = {"woocommerce": to_woocommerce, "shoper": to_shoper}
