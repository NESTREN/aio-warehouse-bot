from __future__ import annotations

import html
from typing import Iterable


def parse_number(value: str) -> float | None:
    raw = value.strip().replace(" ", "")
    raw = raw.replace(",", ".")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 1:
        return text[:limit]
    return text[: limit - 1] + "…"


def format_items_table(items: Iterable[dict]) -> str:
    headers = ["ID", "SKU", "NAME", "QTY", "UNIT", "WH", "LOC", "MIN"]
    rows = []
    for item in items:
        rows.append(
            [
                str(item["id"]),
                truncate(str(item["sku"]), 12),
                truncate(str(item["name"]), 20),
                f"{item['qty']:.2f}".rstrip("0").rstrip("."),
                truncate(str(item["unit"] or ""), 4),
                truncate(str(item["warehouse"] or ""), 8),
                truncate(str(item["location"] or ""), 10),
                f"{item['min_qty']:.2f}".rstrip("0").rstrip("."),
            ]
        )
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(cell))

    def render_row(row: list[str]) -> str:
        return " ".join(cell.ljust(col_widths[idx]) for idx, cell in enumerate(row))

    lines = [render_row(headers)]
    lines.append(" ".join("-" * w for w in col_widths))
    for row in rows:
        lines.append(render_row(row))

    table = "\n".join(lines)
    return f"<pre>{html.escape(table)}</pre>"


def format_movements_table(moves: Iterable[dict]) -> str:
    headers = ["DT", "SKU", "DELTA", "NOTE"]
    rows = []
    for m in moves:
        rows.append(
            [
                truncate(str(m["created_at"]), 19),
                truncate(str(m["sku"]), 12),
                f"{m['delta']:.2f}".rstrip("0").rstrip("."),
                truncate(str(m["note"] or ""), 24),
            ]
        )
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(cell))

    def render_row(row: list[str]) -> str:
        return " ".join(cell.ljust(col_widths[idx]) for idx, cell in enumerate(row))

    lines = [render_row(headers)]
    lines.append(" ".join("-" * w for w in col_widths))
    for row in rows:
        lines.append(render_row(row))

    table = "\n".join(lines)
    return f"<pre>{html.escape(table)}</pre>"


def format_item_card(item: dict) -> str:
    def esc(value: object) -> str:
        return html.escape(str(value))

    def get_field(key: str, default: str = "-") -> str:
        try:
            value = item[key]
        except (KeyError, IndexError, TypeError):
            value = default
        if value is None or value == "":
            value = default
        return esc(value)

    parts = [
        f"ID: {esc(item['id'])}",
        f"SKU: {esc(item['sku'])}",
        f"Название: {esc(item['name'])}",
        f"Остаток: {esc(item['qty'])}",
        f"Ед.: {esc(item['unit'])}",
        f"Склад: {get_field('warehouse')}",
        f"Локация: {esc(item['location'] or '-')}",
        f"Мин.: {esc(item['min_qty'])}",
        f"Обновлено: {esc(item['updated_at'])}",
    ]
    return "\n".join(parts)
