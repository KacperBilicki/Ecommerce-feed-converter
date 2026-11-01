"""Zamienia plik produktowy z hurtowni na gotowy import do sklepu + raport jakości danych.

Przykład:
    python convert.py sample_data/hurtownia_feed.xlsx --platform woocommerce shoper
    python convert.py cennik.csv --image-base-url https://cdn.sklep.pl/foto --out wynik
"""
import argparse
from decimal import Decimal
from pathlib import Path

from feedconv.export import EXPORTERS
from feedconv.pipeline import ERROR, load_table, process
from feedconv.report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="plik XLSX lub CSV z hurtowni")
    parser.add_argument("--platform", nargs="+", choices=sorted(EXPORTERS), default=["woocommerce"])
    parser.add_argument("--out", type=Path, default=Path("output"), help="folder wynikowy")
    parser.add_argument("--image-base-url", default="", help="adres serwera dla zdjęć podanych jako nazwy plików")
    parser.add_argument("--default-vat", type=Decimal, default=Decimal("0.23"))
    parser.add_argument("--net-prices", action="store_true", help="WooCommerce: eksportuj ceny netto")
    args = parser.parse_args()

    result = process(load_table(args.source), image_base_url=args.image_base_url, default_vat=args.default_vat)
    args.out.mkdir(parents=True, exist_ok=True)

    for platform in args.platform:
        target = args.out / f"import_{platform}.csv"
        if platform == "woocommerce":
            EXPORTERS[platform](result.products, target, prices_include_tax=not args.net_prices)
        else:
            EXPORTERS[platform](result.products, target)
        print(f"  {platform:<12} -> {target}")
    report = args.out / "raport_jakosci_danych.xlsx"
    write_report(result, args.source, report)

    warnings = sum(1 for i in result.issues if i.severity != ERROR)
    print(f"\nWierszy w pliku:        {result.total_rows}")
    print(f"Gotowych do importu:    {len(result.products)}")
    print(f"Odrzuconych:            {len(result.rejected)}")
    print(f"Ostrzeżeń:              {warnings}")
    print(f"Raport:                 {report}")


if __name__ == "__main__":
    main()
