"""Przetwarzanie całego pliku: mapowanie, czyszczenie, walidacja, duplikaty."""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

from . import clean
from .columns import map_columns

ERROR = "BŁĄD"
WARNING = "OSTRZEŻENIE"
DEFAULT_VAT = Decimal("0.23")


@dataclass
class Issue:
    row: int          # numer wiersza w Excelu źródłowym (z nagłówkiem = 1)
    ean: str
    name: str
    severity: str
    kind: str         # krótka kategoria do podsumowania
    message: str


@dataclass
class Result:
    products: list[dict] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    mapping: dict = field(default_factory=dict)
    unmapped: list = field(default_factory=list)
    total_rows: int = 0


def load_table(path: Path) -> pd.DataFrame:
    """Wczytuje XLSX/CSV bez zgadywania typów – EAN-y muszą zostać nietknięte."""
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path, dtype=object)
    for encoding in ("utf-8-sig", "cp1250"):
        try:
            return pd.read_csv(path, dtype=str, sep=None, engine="python", encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Nie udało się odczytać pliku {path} (kodowanie)")


def process(df: pd.DataFrame, *, image_base_url: str = "", default_vat: Decimal = DEFAULT_VAT) -> Result:
    mapping, image_cols, unmapped = map_columns(df.columns)
    result = Result(mapping=mapping, unmapped=unmapped, total_rows=len(df))
    missing = {"ean", "name"} - set(mapping.values())
    if missing:
        raise ValueError(f"Nie rozpoznano wymaganych kolumn: {', '.join(sorted(missing))}")
    if not {"price_net", "price_gross"} & set(mapping.values()):
        raise ValueError("Nie rozpoznano kolumny z ceną (netto ani brutto)")

    first_seen: dict[str, int] = {}
    for idx, raw in df.iterrows():
        row_no = idx + 2
        src = {f: raw[c] for c, f in mapping.items()}
        product, issues = _process_row(row_no, src, [raw[c] for c in image_cols], image_base_url, default_vat)

        ean = product["ean"]
        if ean and ean in first_seen:
            issues.append(Issue(row_no, ean, product["name"], ERROR, "Duplikat EAN",
                                f"duplikat EAN – pierwsze wystąpienie w wierszu {first_seen[ean]}"))
        elif ean:
            first_seen[ean] = row_no

        result.issues.extend(issues)
        errors = [i.message for i in issues if i.severity == ERROR]
        if errors:
            result.rejected.append({"wiersz": row_no, "ean_zrodlowy": clean.clean_text(src.get("ean")),
                                    "nazwa": product["name"], "powod": "; ".join(errors)})
        else:
            result.products.append(product)
    return result


def _process_row(row_no, src, image_values, image_base_url, default_vat) -> tuple[dict, list[Issue]]:
    issues: list[Issue] = []
    name = clean.clean_name(src.get("name"))
    ean, ean_problem = clean.clean_ean(src.get("ean"))

    def add(severity, kind, message):
        issues.append(Issue(row_no, ean or clean.clean_text(src.get("ean")), name, severity, kind, message))

    if ean_problem:
        add(ERROR, "EAN", ean_problem)
    if not name:
        add(ERROR, "Brak nazwy", "brak nazwy produktu")

    vat = clean.parse_vat(src.get("vat"))
    if vat is None:
        vat = default_vat
        if "vat" in src:
            add(WARNING, "VAT", f"brak/nieczytelna stawka VAT – przyjęto {int(default_vat * 100)}%")

    net, gross = clean.parse_price(src.get("price_net")), clean.parse_price(src.get("price_gross"))
    if gross is None and net is not None:
        gross = (net * (1 + vat)).quantize(clean.CENT, ROUND_HALF_UP)
    if net is None and gross is not None:
        net = (gross / (1 + vat)).quantize(clean.CENT, ROUND_HALF_UP)
    if gross is None or gross <= 0:
        raw_price = src.get("price_net", src.get("price_gross"))
        add(ERROR, "Cena", f"brak lub nieprawidłowa cena: {clean.clean_text(raw_price) or '(puste)'}")

    stock = clean.parse_stock(src.get("stock"))
    if stock is None and "stock" in src:
        add(WARNING, "Stan magazynowy",
            f"stan nieliczbowy ({clean.clean_text(src.get('stock')) or 'puste'}) – do ustalenia z klientem")

    category = clean.normalize_category(src.get("category"))
    if not category:
        add(WARNING, "Kategoria", "brak kategorii")

    images, relative = clean.collect_images(image_values, image_base_url)
    if relative:
        add(WARNING, "Zdjęcia", f"zdjęcia bez adresu URL ({', '.join(relative)}) – potrzebne pliki lub adres serwera")
    elif not images:
        add(WARNING, "Zdjęcia", "brak zdjęć")

    brand, color = clean.clean_text(src.get("brand")), clean.clean_text(src.get("color"))
    weight = clean.parse_weight(src.get("weight"))
    short, generated = clean.build_description(name, brand, color, weight)
    description = clean.sanitize_html(src.get("description"))
    if not description:
        description = generated
        add(WARNING, "Opis", "brak opisu w pliku – utworzono opis z dostępnych danych")

    product = {
        "source_row": row_no, "ean": ean, "sku": clean.clean_text(src.get("sku")) or ean, "name": name,
        "price_net": net, "price_gross": gross, "vat": vat, "stock": stock, "category": category,
        "brand": brand, "color": color, "weight": weight, "images": images,
        "short_description": short, "description": description,
    }
    return product, issues
