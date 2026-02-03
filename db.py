from __future__ import annotations

import aiosqlite
from datetime import datetime
from typing import Iterable


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        if self._conn is not None:
            return
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def init(self) -> None:
        await self.connect()
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                name TEXT,
                added_at TEXT NOT NULL
            )
            """
        )
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                qty REAL NOT NULL DEFAULT 0,
                unit TEXT NOT NULL DEFAULT 'шт',
                location TEXT,
                warehouse TEXT,
                min_qty REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS warehouses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await self._ensure_column("items", "warehouse")
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
                delta REAL NOT NULL,
                note TEXT,
                admin_tg_id INTEGER,
                created_at TEXT NOT NULL
            )
            """
        )
        await self._conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat(timespec="seconds")

    async def _ensure_column(self, table: str, column: str) -> None:
        cur = await self._conn.execute(f"PRAGMA table_info({table})")
        cols = [row["name"] for row in await cur.fetchall()]
        if column not in cols:
            await self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")

    async def ensure_admins(self, tg_ids: Iterable[int]) -> None:
        for tg_id in tg_ids:
            await self.add_admin(tg_id, name="superadmin", silent=True)

    async def is_admin(self, tg_id: int) -> bool:
        cur = await self._conn.execute(
            "SELECT 1 FROM admins WHERE tg_id = ? LIMIT 1", (tg_id,)
        )
        row = await cur.fetchone()
        return row is not None

    async def list_admins(self) -> list[aiosqlite.Row]:
        cur = await self._conn.execute(
            "SELECT tg_id, name, added_at FROM admins ORDER BY added_at ASC"
        )
        return await cur.fetchall()

    async def add_admin(self, tg_id: int, name: str | None, silent: bool = False) -> bool:
        try:
            await self._conn.execute(
                "INSERT INTO admins (tg_id, name, added_at) VALUES (?, ?, ?)",
                (tg_id, name, self._now()),
            )
            await self._conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False if not silent else True

    async def remove_admin(self, tg_id: int) -> bool:
        cur = await self._conn.execute("DELETE FROM admins WHERE tg_id = ?", (tg_id,))
        await self._conn.commit()
        return cur.rowcount > 0

    async def add_item(
        self,
        sku: str,
        name: str,
        qty: float,
        unit: str,
        location: str | None,
        warehouse: str | None,
        min_qty: float,
    ) -> bool:
        try:
            await self._conn.execute(
                """
                INSERT INTO items (sku, name, qty, unit, location, warehouse, min_qty, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sku, name, qty, unit, location, warehouse, min_qty, self._now()),
            )
            await self._conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def get_item_by_id(self, item_id: int) -> aiosqlite.Row | None:
        cur = await self._conn.execute(
            "SELECT * FROM items WHERE id = ?", (item_id,)
        )
        return await cur.fetchone()

    async def get_item_by_sku(self, sku: str) -> aiosqlite.Row | None:
        cur = await self._conn.execute(
            "SELECT * FROM items WHERE lower(sku) = lower(?)", (sku,)
        )
        return await cur.fetchone()

    async def get_item_by_key(self, key: str) -> aiosqlite.Row | None:
        key = key.strip()
        if key.isdigit():
            item = await self.get_item_by_id(int(key))
            if item:
                return item
        return await self.get_item_by_sku(key)

    async def list_items(self, limit: int, offset: int) -> list[aiosqlite.Row]:
        cur = await self._conn.execute(
            """
            SELECT * FROM items
            ORDER BY name ASC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return await cur.fetchall()

    async def count_items(self) -> int:
        cur = await self._conn.execute("SELECT COUNT(*) AS c FROM items")
        row = await cur.fetchone()
        return int(row["c"]) if row else 0

    async def search_items(self, query: str, limit: int = 50) -> list[aiosqlite.Row]:
        like = f"%{query.strip()}%"
        cur = await self._conn.execute(
            """
            SELECT * FROM items
            WHERE sku LIKE ? OR name LIKE ?
            ORDER BY name ASC
            LIMIT ?
            """,
            (like, like, limit),
        )
        return await cur.fetchall()

    async def list_low_stock(self, limit: int = 100) -> list[aiosqlite.Row]:
        cur = await self._conn.execute(
            """
            SELECT * FROM items
            WHERE min_qty > 0 AND qty <= min_qty
            ORDER BY qty ASC
            LIMIT ?
            """,
            (limit,),
        )
        return await cur.fetchall()

    async def update_item_qty(self, item_id: int, new_qty: float) -> None:
        await self._conn.execute(
            "UPDATE items SET qty = ?, updated_at = ? WHERE id = ?",
            (new_qty, self._now(), item_id),
        )
        await self._conn.commit()

    async def adjust_item_qty(self, item_id: int, delta: float) -> None:
        await self._conn.execute(
            "UPDATE items SET qty = qty + ?, updated_at = ? WHERE id = ?",
            (delta, self._now(), item_id),
        )
        await self._conn.commit()

    async def update_item_fields(
        self,
        item_id: int,
        name: str | None = None,
        sku: str | None = None,
        unit: str | None = None,
        location: str | None = None,
        warehouse: str | None = None,
        min_qty: float | None = None,
    ) -> bool:
        parts = []
        values: list[object] = []
        if name is not None:
            parts.append("name = ?")
            values.append(name)
        if sku is not None:
            parts.append("sku = ?")
            values.append(sku)
        if unit is not None:
            parts.append("unit = ?")
            values.append(unit)
        if location is not None:
            parts.append("location = ?")
            values.append(location)
        if warehouse is not None:
            parts.append("warehouse = ?")
            values.append(warehouse)
        if min_qty is not None:
            parts.append("min_qty = ?")
            values.append(min_qty)
        parts.append("updated_at = ?")
        values.append(self._now())
        values.append(item_id)
        sql = "UPDATE items SET " + ", ".join(parts) + " WHERE id = ?"
        try:
            await self._conn.execute(sql, values)
            await self._conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def delete_item(self, item_id: int) -> bool:
        cur = await self._conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        await self._conn.commit()
        return cur.rowcount > 0

    async def add_movement(
        self, item_id: int, delta: float, note: str | None, admin_tg_id: int
    ) -> None:
        await self._conn.execute(
            """
            INSERT INTO movements (item_id, delta, note, admin_tg_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (item_id, delta, note, admin_tg_id, self._now()),
        )
        await self._conn.commit()

    async def list_movements(self, limit: int = 50) -> list[aiosqlite.Row]:
        cur = await self._conn.execute(
            """
            SELECT m.id, m.delta, m.note, m.admin_tg_id, m.created_at,
                   i.sku, i.name
            FROM movements m
            JOIN items i ON i.id = m.item_id
            ORDER BY m.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return await cur.fetchall()

    async def export_items(self) -> list[aiosqlite.Row]:
        cur = await self._conn.execute(
            "SELECT * FROM items ORDER BY name ASC"
        )
        return await cur.fetchall()

    async def add_warehouse(self, name: str) -> bool:
        try:
            await self._conn.execute(
                "INSERT INTO warehouses (name, created_at) VALUES (?, ?)",
                (name, self._now()),
            )
            await self._conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

    async def get_warehouse_by_name(self, name: str) -> aiosqlite.Row | None:
        cur = await self._conn.execute(
            "SELECT id, name FROM warehouses WHERE name = ?", (name,)
        )
        return await cur.fetchone()

    async def list_warehouses(self) -> list[aiosqlite.Row]:
        cur = await self._conn.execute(
            "SELECT id, name FROM warehouses ORDER BY name ASC"
        )
        return await cur.fetchall()

    async def get_warehouse_by_id(self, warehouse_id: int) -> aiosqlite.Row | None:
        cur = await self._conn.execute(
            "SELECT id, name FROM warehouses WHERE id = ?", (warehouse_id,)
        )
        return await cur.fetchone()

    async def count_items_by_warehouse(self, warehouse_name: str | None) -> int:
        if warehouse_name is None:
            return await self.count_items()
        cur = await self._conn.execute(
            "SELECT COUNT(*) AS c FROM items WHERE warehouse = ?", (warehouse_name,)
        )
        row = await cur.fetchone()
        return int(row["c"]) if row else 0

    async def list_items_by_warehouse(
        self, warehouse_name: str | None, sort: str, limit: int, offset: int
    ) -> list[aiosqlite.Row]:
        order = "name ASC"
        if sort == "qty":
            order = "qty ASC"
        elif sort == "sku":
            order = "sku ASC"
        if warehouse_name is None:
            cur = await self._conn.execute(
                f"SELECT * FROM items ORDER BY {order} LIMIT ? OFFSET ?",
                (limit, offset),
            )
        else:
            cur = await self._conn.execute(
                f"SELECT * FROM items WHERE warehouse = ? ORDER BY {order} LIMIT ? OFFSET ?",
                (warehouse_name, limit, offset),
            )
        return await cur.fetchall()
