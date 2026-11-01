"""Czyszczenie pojedynczych wartości. Każda funkcja jest czysta i testowalna."""
import html
import math
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
ALLOWED_TAGS = {"p", "br", "ul", "ol", "li", "b", "strong", "i", "em", "h3", "h4"}
UNITS = {"v": "V", "w": "W", "kw": "kW", "ah": "Ah", "mah": "mAh", "hz": "Hz", "led": "LED", "usb": "USB"}


def is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == ""


# --- EAN / GTIN ---------------------------------------------------------------

def gtin_checksum_ok(code: str) -> bool:
    body, check = code[:-1], int(code[-1])
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


def clean_ean(value) -> tuple[str | None, str | None]:
    """Zwraca (EAN, None) albo (None, opis problemu)."""
    if is_blank(value):
        return None, "brak EAN"
    if isinstance(value, float):
        if not value.is_integer():
            return None, f"EAN nie jest liczbą całkowitą: {value}"
        code = str(int(value))
    elif isinstance(value, int):
        code = str(value)
    else:
        text = str(value).strip()
        if re.fullmatch(r"\d+(?:[.,]\d+)?[eE]\+?\d+", text):
            return None, f"EAN zniekształcony przez Excela (notacja naukowa: {text}) – potrzebny oryginał"
        code = re.sub(r"[\s\-]", "", text)
        code = code[:-2] if code.endswith(".0") else code
    if not code.isdigit():
        return None, f"EAN zawiera niedozwolone znaki: {value!r}"
    if len(code) in (11, 12):  # UPC-A albo zero wiodące zgubione przez Excela
        code = code.zfill(13)
    if len(code) not in (8, 13, 14):
        return None, f"nieprawidłowa długość EAN ({len(code)} cyfr)"
    if not gtin_checksum_ok(code):
        return None, f"błędna cyfra kontrolna EAN ({code})"
    return code, None


# --- liczby -------------------------------------------------------------------

def parse_price(value) -> Decimal | None:
    """'1 299,00 PLN', '12.99 zł', 12.99 -> Decimal('12.99')."""
    if is_blank(value):
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value)).quantize(CENT, ROUND_HALF_UP)
    text = re.sub(r"(zł|pln)", "", str(value).lower())
    text = re.sub(r"[\s ]", "", text)
    if "," in text and "." in text:  # separator dziesiętny to ten, który występuje ostatni
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    else:
        text = text.replace(",", ".")
    try:
        return Decimal(text).quantize(CENT, ROUND_HALF_UP)
    except InvalidOperation:
        return None


def parse_vat(value) -> Decimal | None:
    """'23%', '8 %', 23, 0.23, 'zw' -> ułamek (Decimal('0.23'))."""
    if is_blank(value):
        return None
    text = str(value).strip().lower().replace("%", "").replace(",", ".").strip()
    if text in ("zw", "np", "0"):
        return Decimal("0")
    try:
        rate = Decimal(text)
    except InvalidOperation:
        return None
    return (rate / 100 if rate >= 1 else rate).quantize(CENT)


def parse_stock(value) -> int | None:
    """Liczba sztuk; None, gdy hurtownia podaje tylko 'dostępny' itp."""
    if is_blank(value):
        return None
    if isinstance(value, (int, float)):
        return max(int(value), 0)
    text = str(value).strip().lower()
    if text in ("brak", "niedostępny", "niedostepny", "0"):
        return 0
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def parse_weight(value) -> Decimal | None:
    price_like = parse_price(value)
    return price_like if price_like and price_like > 0 else None


# --- teksty -------------------------------------------------------------------

def clean_text(value) -> str:
    return "" if is_blank(value) else re.sub(r"\s+", " ", str(value)).strip()


def clean_name(value) -> str:
    """Usuwa nadmiarowe spacje; nazwy pisane CAPS LOCKIEM zamienia na zdanie.

    Tokeny z cyframi (np. '20L', '5W') zostają bez zmian, jednostki dostają poprawny zapis.
    """
    name = clean_text(value)
    if name and name.upper() == name and any(c.isalpha() for c in name):
        words = [w if any(c.isdigit() for c in w) else UNITS.get(w.lower(), w.lower()) for w in name.split(" ")]
        name = " ".join(words)
        name = name[0].upper() + name[1:]
    return name


def normalize_category(value) -> str:
    """'dom/kuchnia', 'Dom - Kuchnia', 'Dom>Kuchnia' -> 'Dom > Kuchnia'."""
    text = clean_text(value)
    if not text:
        return ""
    parts = [p.strip() for p in re.split(r"\s*(?:>|/|\\|\||\s-\s)\s*", text) if p.strip()]
    return " > ".join(p[0].upper() + p[1:] for p in parts)


def collect_images(values, base_url: str = "") -> tuple[list[str], list[str]]:
    """Zwraca (lista adresów zdjęć bez duplikatów, pliki bez pełnego adresu URL)."""
    images, relative = [], []
    for value in values:
        for item in re.split(r"[;,|\s]+", clean_text(value)):
            if not item:
                continue
            if not item.lower().startswith(("http://", "https://")):
                if not base_url:
                    relative.append(item)
                    continue
                item = base_url.rstrip("/") + "/" + item.lstrip("/")
            if item not in images:
                images.append(item)
    return images, relative


def sanitize_html(value) -> str:
    """Zostawia tylko bezpieczne tagi bez atrybutów; zwykły tekst opakowuje w <p>."""
    text = "" if is_blank(value) else str(value).strip()
    if not text:
        return ""
    if not re.search(r"<[a-zA-Z/][^>]*>", text):
        return "".join(f"<p>{html.escape(p.strip())}</p>" for p in re.split(r"\n{2,}", text) if p.strip())
    text = re.sub(r"<(script|style)\b.*?</\1>", "", text, flags=re.S | re.I)

    def keep_allowed(match: re.Match) -> str:
        closing, tag = match.group(1), match.group(2).lower()
        if tag in ALLOWED_TAGS:
            return f"<{closing}{tag}>"
        return " " if tag in ("div", "span") else ""

    text = re.sub(r"<(/?)([a-zA-Z0-9]+)[^>]*>", keep_allowed, text)
    text = re.sub(r"(<br>\s*){2,}", "<br>", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def build_description(name: str, brand: str, color: str, weight: Decimal | None) -> tuple[str, str]:
    """Krótki i długi opis zbudowany wyłącznie z danych z pliku – bez wymyślania parametrów."""
    facts = [("Producent", brand), ("Kolor", color), ("Waga", f"{weight} kg" if weight else "")]
    facts = [(label, value) for label, value in facts if value]
    short = " · ".join(f"{label}: {value}" for label, value in facts) or name
    items = "".join(f"<li><strong>{label}:</strong> {html.escape(value)}</li>" for label, value in facts)
    long = f"<p>{html.escape(name)}</p>" + (f"<ul>{items}</ul>" if items else "")
    return short, long
