"""CLI: разовая выгрузка из GHL в .xlsx.

Запуск:
    python -m scripts.export_to_excel
    python -m scripts.export_to_excel --out ./exports/today.xlsx
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from app.export.excel import export_to_excel


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Export CRM data from GHL to Excel")
    parser.add_argument("--out", type=Path, default=None, help="Путь к .xlsx файлу")
    args = parser.parse_args()

    path = asyncio.run(export_to_excel(out_path=args.out))
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
