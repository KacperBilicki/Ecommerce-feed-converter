"""Raport dla klienta w Excelu: co weszło, co odrzucono i dlaczego."""
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .pipeline import ERROR, Result

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
ERROR_FILL = PatternFill("solid", fgColor="F8D7DA")
WARNING_FILL = PatternFill("solid", fgColor="FFF3CD")


def write_report(result: Result, source: Path, path: Path) -> None:
    issues = pd.DataFrame([vars(i) for i in result.issues],
                          columns=["row", "ean", "name", "severity", "kind", "message"])
    issues.columns = ["Wiersz w pliku", "EAN", "Nazwa", "Waga problemu", "Rodzaj", "Opis"]
    with_warnings = issues.loc[issues["Waga problemu"] != ERROR, "Wiersz w pliku"].nunique()

    summary = [
        ("Data raportu", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ("Plik źródłowy", source.name),
        ("Wierszy w pliku", result.total_rows),
        ("Gotowych do importu", len(result.products)),
        ("Odrzuconych (wymagają danych od klienta)", len(result.rejected)),
        ("Wierszy z ostrzeżeniami", with_warnings),
        ("", ""),
        ("Rozpoznane kolumny", ", ".join(f"{c} → {f}" for c, f in result.mapping.items())),
        ("Pominięte kolumny", ", ".join(map(str, result.unmapped)) or "—"),
        ("", ""),
        ("PROBLEMY WG RODZAJU", "Liczba"),
    ]
    counts = Counter(zip(issues["Waga problemu"], issues["Rodzaj"]))
    summary += [(f"{sev}: {kind}", n) for (sev, kind), n in counts.most_common()]

    preview = pd.DataFrame([{
        "EAN": p["ean"], "SKU": p["sku"], "Nazwa": p["name"], "Cena netto": float(p["price_net"]),
        "Cena brutto": float(p["price_gross"]), "VAT": f"{int(p['vat'] * 100)}%", "Stan": p["stock"],
        "Kategoria": p["category"], "Zdjęć": len(p["images"]),
    } for p in result.products])
    rejected = pd.DataFrame(result.rejected, columns=["wiersz", "ean_zrodlowy", "nazwa", "powod"])
    rejected.columns = ["Wiersz w pliku", "EAN w pliku", "Nazwa", "Powód odrzucenia"]

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(summary, columns=["Pozycja", "Wartość"]).to_excel(writer, sheet_name="Podsumowanie", index=False)
        rejected.to_excel(writer, sheet_name="Odrzucone", index=False)
        issues.to_excel(writer, sheet_name="Wszystkie problemy", index=False)
        preview.to_excel(writer, sheet_name="Do importu", index=False)
        for ws in writer.book.worksheets:
            _style(ws)


def _style(ws) -> None:
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for col in ws.columns:
        width = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max(width + 2, 10), 70)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=len(str(cell.value or "")) > 70)
            if cell.value == ERROR or ws.title == "Odrzucone":
                cell.fill = ERROR_FILL
            elif cell.value == "OSTRZEŻENIE":
                cell.fill = WARNING_FILL
