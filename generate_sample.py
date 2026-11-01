"""Generuje przykładowy, celowo "brudny" plik produktowy z hurtowni.

Plik odwzorowuje typowe problemy z prawdziwych zleceń: różne formaty cen,
EAN-y zepsute przez Excela, duplikaty, nazwy CAPS LOCKIEM, braki zdjęć itd.
Dane są fikcyjne (marki, produkty, adresy zdjęć).

Użycie:
    python generate_sample.py [--rows 400] [--out sample_data/hurtownia_feed.xlsx]
"""
import argparse
import random
from pathlib import Path

from openpyxl import Workbook

CATALOG = {
    "Dom > Kuchnia": [
        "Patelnia {material} {size} cm",
        "Garnek {material} {cap} l",
        "Deska do krojenia {material}",
        "Nóż szefa kuchni {size} cm",
        "Zestaw sztućców {n} el.",
    ],
    "Dom > Łazienka": [
        "Dozownik do mydła {material}",
        "Ręcznik kąpielowy {dim}x{size2} cm",
        "Mata łazienkowa {dim}x{size2} cm",
    ],
    "Ogród > Narzędzia ogrodowe": [
        "Sekator nożycowy {size} mm",
        "Wąż ogrodowy {size} m",
        "Grabie {material}",
        "Konewka {cap} l",
    ],
    "Narzędzia > Elektronarzędzia": [
        "Wiertarka udarowa {w} W",
        "Szlifierka kątowa {w} W",
        "Wkrętarka akumulatorowa {v} V",
    ],
}
BRANDS = ["Kuchmistrz", "GardenPro", "Majster", "Aqualine", "Domino"]
MATERIALS = ["ze stali nierdzewnej", "z aluminium", "z bambusa", "z ceramiki", "z tworzywa"]
COLORS = ["czarny", "biały", "szary", "czerwony", "zielony", "srebrny", None]
DESCRIPTIONS = [
    "Solidne wykonanie i wygodny uchwyt. Produkt przeznaczony do codziennego użytku.",
    "Lekki i poręczny. Łatwy w czyszczeniu.",
    '<div class="desc"><span style="color:#333;font-size:13px">Trwały materiał, '
    'odporny na zarysowania.</span><br><br><b>Gwarancja 24 miesiące.</b></div>',
    "<p style='margin:0'>Idealny do domu i ogrodu.</p><ul><li>wysoka jakość</li>"
    "<li>prosty montaż</li></ul>",
]
SEPARATORS = [" > ", "/", " - ", ">", " | "]

HEADERS = [
    "Kod EAN", "Symbol", "Nazwa towaru", "Cena netto [PLN]", "Stawka VAT",
    "Stan mag.", "Kategoria", "Producent", "Kolor", "Waga (kg)", "Opis",
    "Zdjęcie 1", "Zdjęcie 2", "Uwagi hurtowni",
]


def gtin_check_digit(body: str) -> str:
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return str((10 - total % 10) % 10)


def make_ean(rng: random.Random, prefix: str = "590") -> str:
    body = prefix + "".join(rng.choice("0123456789") for _ in range(12 - len(prefix)))
    return body + gtin_check_digit(body)


def make_name(rng: random.Random, template: str) -> str:
    return template.format(
        material=rng.choice(MATERIALS), size=rng.choice([16, 20, 24, 28, 30, 50, 70]),
        dim=rng.choice([40, 50, 60]), size2=rng.choice([70, 100, 140]), cap=rng.choice([1.5, 3, 5, 10]),
        n=rng.choice([12, 24, 36]), w=rng.choice([500, 750, 900, 1200]),
        v=rng.choice([12, 18, 20]),
    )


def messy_price(rng: random.Random, value: float):
    roll = rng.random()
    if roll < 0.02:
        return None
    if roll < 0.03:
        return "0"
    if roll < 0.45:
        return round(value, 2)
    if roll < 0.70:
        return f"{value:.2f}".replace(".", ",")
    if roll < 0.85:
        return f"{value:.2f} zł"
    whole, frac = f"{value:.2f}".split(".")
    return f"{int(whole):,}".replace(",", " ") + f",{frac} PLN"


def messy_ean(rng: random.Random, ean: str):
    roll = rng.random()
    if roll < 0.03:
        return None
    if roll < 0.06:  # zła cyfra kontrolna (literówka)
        return int(ean[:-1] + str((int(ean[-1]) + 3) % 10))
    if roll < 0.09:  # CSV otwarty w Excelu -> notacja naukowa
        return f"{int(ean[:6]) / 100000:.5f}".replace(".", ",") + "E+12"
    if roll < 0.20:
        return f"{ean[:3]} {ean[3:7]} {ean[7:]}"
    return int(ean)


def messy_stock(rng: random.Random):
    return rng.choice([rng.randint(0, 80)] * 6 + ["brak", ">10", f"{rng.randint(1, 9)} szt.", "dostępny", None])


def messy_vat(rng: random.Random):
    return rng.choice(["23%"] * 6 + [0.23, 23, "8 %", None])


def generate(rows: int, seed: int = 42) -> list[list]:
    rng = random.Random(seed)
    data = []
    for i in range(rows):
        category = rng.choice(list(CATALOG))
        name = make_name(rng, rng.choice(CATALOG[category]))
        sku = f"HD-{10000 + i}"
        # część towarów importowanych ma EAN z zerem wiodącym (UPC-A), które Excel gubi
        ean = make_ean(rng, prefix="0" + str(rng.randint(10, 99))) if rng.random() < 0.05 else make_ean(rng)

        if rng.random() < 0.10:
            name = name.upper()
        if rng.random() < 0.15:
            name = "  " + name.replace(" ", "  ", 1) + " "

        cat = category if rng.random() > 0.04 else None
        if cat:
            cat = rng.choice(SEPARATORS).join(cat.split(" > "))
            if rng.random() < 0.2:
                cat = cat.lower()

        images = [None, None]
        roll = rng.random()
        if roll < 0.70:
            images = [f"https://example.com/img/{sku}_1.jpg",
                      f"https://example.com/img/{sku}_2.jpg" if rng.random() < 0.6 else None]
        elif roll < 0.85:
            images = [f"IMG_{4000 + i}.jpg", None]

        data.append([
            messy_ean(rng, ean), sku, name, messy_price(rng, rng.uniform(9, 900)), messy_vat(rng),
            messy_stock(rng), cat, rng.choice(BRANDS + [None]), rng.choice(COLORS),
            rng.choice([round(rng.uniform(0.1, 6), 2), None]),
            rng.choice(DESCRIPTIONS + [None, None, None]), images[0], images[1],
            rng.choice([None, None, "nowość", "wycofywany", "promocja do końca miesiąca"]),
        ])

    # duplikaty: te same produkty wklejone drugi raz (czasem z inną ceną)
    for _ in range(max(1, rows // 30)):
        dup = list(rng.choice(data))
        if rng.random() < 0.5:
            dup[3] = messy_price(rng, rng.uniform(9, 900))
        data.insert(rng.randrange(len(data)), dup)
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rows", type=int, default=400)
    parser.add_argument("--out", default="sample_data/hurtownia_feed.xlsx")
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Cennik"
    ws.append(HEADERS)
    for row in generate(args.rows):
        ws.append(row)
    wb.save(out)
    print(f"Zapisano {ws.max_row - 1} wierszy do {out}")


if __name__ == "__main__":
    main()
