import asyncio
import csv
import io
import math
import os
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.types.input_file import BufferedInputFile, FSInputFile

from config import load_config
from constants import (
    BTN_ADD_ITEM,
    BTN_ADMIN,
    BTN_ADJUST_QTY,
    BTN_BACK,
    BTN_BULK_ADD,
    BTN_CANCEL,
    BTN_DELETE_ITEM,
    BTN_EXPORT_CSV,
    BTN_HELP,
    BTN_HISTORY,
    BTN_LOW_STOCK,
    BTN_LIST_ITEMS,
    BTN_REPORTS,
    BTN_SEARCH,
    BTN_SETTINGS,
    BTN_SET_QTY,
    BTN_WAREHOUSES,
    BTN_WAREHOUSE,
)
from db import Database
from filters import IsAdmin
from keyboards import (
    admin_menu_kb,
    main_menu_kb,
    pagination_kb,
    reports_menu_kb,
    search_menu_kb,
    settings_menu_kb,
    update_fields_kb,
    warehouses_menu_kb,
    warehouse_filter_kb,
    warehouse_sort_kb,
    warehouses_select_kb,
    warehouse_menu_kb,
)
from middleware import ConfigMiddleware, DbMiddleware
from states import (
    AddAdmin,
    AddItem,
    AddWarehouse,
    BulkAdd,
    AdjustItem,
    DeleteItem,
    RemoveAdmin,
    SearchItem,
    SetQty,
    UpdateItem,
)
from utils import (
    format_item_card,
    format_items_table,
    format_movements_table,
    parse_number,
)

PAGE_SIZE = 10
logger = logging.getLogger(__name__)

public_router = Router()
admin_router = Router()
admin_router.message.filter(IsAdmin())
admin_router.callback_query.filter(IsAdmin())


def is_cancel(text: str | None) -> bool:
    return (text or "").strip().lower() in {"/cancel", BTN_CANCEL.lower(), "отмена"}


def is_super_admin(user_id: int, config) -> bool:
    return user_id in config.super_admins


async def show_main_menu(message: Message) -> None:
    await message.answer(
        "🏠 Главное меню — выберите действие:\n"
        "Подсказка: можно жать кнопки или писать команды.",
        reply_markup=main_menu_kb(),
    )


async def render_items_page(db: Database, page: int) -> tuple[str, int]:
    total = await db.count_items()
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    items = await db.list_items(PAGE_SIZE, (page - 1) * PAGE_SIZE)
    if not items:
        return "Товаров пока нет.", total_pages
    table = format_items_table(items)
    text = f"Список товаров ({page}/{total_pages})\n{table}"
    return text, total_pages


async def render_items_by_warehouse(
    db: Database, warehouse_name: str | None, sort: str, page: int
) -> tuple[str, int]:
    total = await db.count_items_by_warehouse(warehouse_name)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    items = await db.list_items_by_warehouse(warehouse_name, sort, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    label = warehouse_name or "Все склады"
    if not items:
        return f"Товаров нет ({label}).", total_pages
    table = format_items_table(items)
    text = f"Склад: {label} | сортировка: {sort} ({page}/{total_pages})\\n{table}"
    return text, total_pages


def parse_bulk_lines(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        reader = csv.reader([line], delimiter=",", skipinitialspace=True)
        rows.extend([list(r) for r in reader])
    return rows


def build_prefill_kb(items: list) -> InlineKeyboardMarkup | None:
    if not items:
        return None
    rows = []
    for item in items[:5]:
        text = f"Шаблон: {item['sku']} ({item['name']})"
        rows.append([InlineKeyboardButton(text=text, callback_data=f"prefill_item:{item['id']}")])
    rows.append([InlineKeyboardButton(text="Без шаблона", callback_data="prefill_item:skip")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def build_warehouse_select(db: Database) -> InlineKeyboardMarkup:
    warehouses = await db.list_warehouses()
    return warehouses_select_kb(warehouses)


@public_router.message(CommandStart())
async def cmd_start(message: Message, db: Database) -> None:
    if await db.is_admin(message.from_user.id):
        await message.answer("Привет! Я склад‑бот и готов работать ✅")
        await show_main_menu(message)
    else:
        logger.warning("Access denied for user_id=%s", message.from_user.id)
        await message.answer("⛔ Доступ закрыт. Обратитесь к администратору.")


@public_router.callback_query()
async def public_callback(callback: CallbackQuery, db: Database) -> None:
    if await db.is_admin(callback.from_user.id):
        return
    await callback.answer("⛔ Доступ закрыт", show_alert=True)


@public_router.message()
async def public_fallback(message: Message, db: Database) -> None:
    if await db.is_admin(message.from_user.id):
        return
    await message.answer("⛔ Доступ закрыт. Обратитесь к администратору.")


@admin_router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await show_main_menu(message)


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    await show_main_menu(message)


@admin_router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    await message.answer(f"Ваш Telegram ID: {message.from_user.id}", reply_markup=main_menu_kb())


@admin_router.message(Command("help"))
@admin_router.message(F.text == BTN_HELP)
async def cmd_help(message: Message) -> None:
    text = (
        "ℹ️ Помощь по боту‑складу:\n"
        "• ➕ Добавить товар\n"
        "• ➖ Изменить остаток (+/−)\n"
        "• ✅ Установить остаток\n"
        "• 🔍 Поиск / 📋 списки / ⚠️ низкие остатки\n"
        "\n"
        "Можно всегда написать `Отмена` или `/cancel`."
    )
    await message.answer(text, reply_markup=main_menu_kb())


@admin_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("⏹️ Действие отменено.", reply_markup=main_menu_kb())


@admin_router.message(F.text.in_({BTN_CANCEL, "Отмена", "отмена", "⏹️ Отмена"}))
async def cancel_any_state(message: Message, state: FSMContext) -> None:
    if not await state.get_state():
        return
    await state.clear()
    await message.answer("⏹️ Действие отменено.", reply_markup=main_menu_kb())


@admin_router.message(F.text == BTN_WAREHOUSE)
async def menu_warehouse(message: Message) -> None:
    await message.answer("🏬 Раздел: Склад", reply_markup=warehouse_menu_kb())


@admin_router.message(F.text == BTN_BULK_ADD)
@admin_router.callback_query(F.data == "bulk_add")
async def bulk_add_start(event, state: FSMContext) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event
    await state.set_state(BulkAdd.lines)
    text = (
        "📥 Массовая заливка\n"
        "Отправьте список товаров, по одному в строке.\n"
        "\n"
        "Формат (CSV через запятую):\n"
        "sku,name,qty,unit,location,warehouse,min_qty\n"
        "\n"
        "Пример:\n"
        "A-001,Кабель USB,10,шт,Стеллаж 1,Склад А,2\n"
        "A-002,Адаптер,5,шт,,Склад А,0\n"
        "\n"
        "Можно указать только первые 3 поля: sku,name,qty"
    )
    await message.answer(text)


@admin_router.message(F.text == BTN_REPORTS)
async def menu_reports(message: Message) -> None:
    await message.answer("📊 Раздел: Отчеты", reply_markup=reports_menu_kb())


@admin_router.message(F.text == BTN_ADMIN)
async def menu_admin(message: Message) -> None:
    await message.answer("🛠️ Админ‑панель", reply_markup=admin_menu_kb())


@admin_router.message(F.text == BTN_SETTINGS)
async def menu_settings(message: Message) -> None:
    await message.answer("⚙️ Настройки", reply_markup=settings_menu_kb())


@admin_router.message(F.text == BTN_WAREHOUSES)
async def menu_warehouses(message: Message) -> None:
    await message.answer("🏢 Склады", reply_markup=warehouses_menu_kb())


@admin_router.callback_query(F.data == "settings_menu")
async def settings_menu_cb(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("⚙️ Настройки", reply_markup=settings_menu_kb())


@admin_router.callback_query(F.data == "warehouses_menu")
async def warehouses_menu_cb(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("🏢 Склады", reply_markup=warehouses_menu_kb())


@admin_router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery) -> None:
    await callback.message.answer("Главное меню", reply_markup=main_menu_kb())
    await callback.answer()


# Добавление товара
@admin_router.message(F.text == BTN_ADD_ITEM)
@admin_router.callback_query(F.data == "add_item")
async def add_item_start(event, state: FSMContext) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event
    await state.set_state(AddItem.sku)
    await message.answer("Введите SKU товара (уникальный код):")


@admin_router.message(AddItem.sku)
async def add_item_sku(message: Message, state: FSMContext, db: Database) -> None:
    sku = message.text.strip()
    if not sku:
        await message.answer("SKU не может быть пустым. Введите SKU:")
        return
    if await db.get_item_by_sku(sku):
        await message.answer("Такой SKU уже есть. Введите другой SKU:")
        return
    await state.update_data(sku=sku)
    await state.set_state(AddItem.name)
    await message.answer("Введите название товара:")


@admin_router.message(AddItem.name)
async def add_item_name(message: Message, state: FSMContext, db: Database) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым. Введите название:")
        return
    await state.update_data(name=name)
    await state.set_state(AddItem.qty)
    suggestions = await db.search_items(name)
    kb = build_prefill_kb(suggestions)
    if kb:
        await message.answer(
            "Есть похожие товары. Выберите шаблон или пропустите:",
            reply_markup=kb,
        )
    await message.answer("Введите начальный остаток (число):")


@admin_router.callback_query(F.data.startswith("prefill_item:"))
async def add_item_prefill(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    if callback.data.endswith(":skip"):
        await callback.message.answer("Шаблон пропущен.")
        return
    item_id = int(callback.data.split(":", 1)[1])
    item = await db.get_item_by_id(item_id)
    if not item:
        await callback.message.answer("Шаблон не найден.")
        return
    await state.update_data(
        unit=item["unit"],
        location=item["location"],
        min_qty=item["min_qty"],
        warehouse=item["warehouse"],
    )
    await callback.message.answer(
        "Шаблон применен: единица, локация, склад и мин. остаток взяты из выбранного товара."
    )


@admin_router.message(AddItem.qty)
async def add_item_qty(message: Message, state: FSMContext) -> None:
    qty = parse_number(message.text)
    if qty is None:
        await message.answer("Нужно число. Пример: 12.5")
        return
    await state.update_data(qty=qty)
    await state.set_state(AddItem.unit)
    await message.answer("Единица измерения (например, шт/кг). Можно '-' для 'шт':")


@admin_router.message(AddItem.unit)
async def add_item_unit(message: Message, state: FSMContext) -> None:
    unit = message.text.strip()
    data = await state.get_data()
    if unit == "-" and data.get("unit"):
        unit = data["unit"]
    elif unit == "-" or not unit:
        unit = "шт"
    await state.update_data(unit=unit)
    await state.set_state(AddItem.location)
    await message.answer("Локация на складе (можно '-' чтобы пропустить):")


@admin_router.message(AddItem.location)
async def add_item_location(message: Message, state: FSMContext, db: Database) -> None:
    location = message.text.strip()
    data = await state.get_data()
    if location == "-" and data.get("location") is not None:
        location = data.get("location")
    elif location == "-":
        location = None
    await state.update_data(location=location)
    await state.set_state(AddItem.warehouse)
    existing = data.get("warehouse")
    hint = "Выберите склад для товара:"
    if existing:
        hint = f"Склад по шаблону: {existing}. Выберите другой или пропустите:"
    await message.answer(hint, reply_markup=await build_warehouse_select(db))


@admin_router.callback_query(AddItem.warehouse, F.data.startswith("warehouse_select:"))
async def add_item_warehouse_select(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    raw_id = callback.data.split(":", 1)[1]
    if not raw_id or raw_id == "0":
        data = await state.get_data()
        warehouse = data.get("warehouse")
        if warehouse is None:
            await state.update_data(warehouse=None)
        await state.set_state(AddItem.min_qty)
        await callback.message.answer("Минимальный остаток (число, можно 0):")
        return
    wh = await db.get_warehouse_by_id(int(raw_id))
    if not wh:
        await callback.message.answer("Склад не найден. Выберите из списка.")
        return
    await state.update_data(warehouse=wh["name"])
    await state.set_state(AddItem.min_qty)
    await callback.message.answer("Минимальный остаток (число, можно 0):")


@admin_router.message(AddItem.min_qty)
async def add_item_min(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    if message.text.strip() == "-" and data.get("min_qty") is not None:
        min_qty = data.get("min_qty")
    else:
        min_qty = parse_number(message.text)
        if min_qty is None:
            await message.answer("Нужно число. Пример: 5")
            return
    ok = await db.add_item(
        sku=data["sku"],
        name=data["name"],
        qty=data["qty"],
        unit=data["unit"],
        location=data.get("location"),
        warehouse=data.get("warehouse"),
        min_qty=min_qty,
    )
    await state.clear()
    if not ok:
        await message.answer("Не удалось добавить товар (SKU уже существует).")
        return
    item = await db.get_item_by_sku(data["sku"])
    await message.answer(
        "Товар добавлен.\n" + format_item_card(item),
        reply_markup=main_menu_kb(),
    )


# Изменить остаток (+/-)
@admin_router.message(F.text == BTN_ADJUST_QTY)
@admin_router.callback_query(F.data == "adjust_qty")
async def adjust_qty_start(event, state: FSMContext) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event
    await state.set_state(AdjustItem.key)
    await message.answer("Введите SKU или ID товара:")


@admin_router.message(AdjustItem.key)
async def adjust_qty_key(message: Message, state: FSMContext, db: Database) -> None:
    item = await db.get_item_by_key(message.text)
    if not item:
        await message.answer("Товар не найден. Введите SKU или ID:")
        return
    await state.update_data(item_id=item["id"], current_qty=item["qty"])
    await state.set_state(AdjustItem.delta)
    await message.answer(
        f"Товар найден:\n{format_item_card(item)}\n\nВведите изменение остатка (например +5 или -3.5):"
    )


@admin_router.message(AdjustItem.delta)
async def adjust_qty_delta(message: Message, state: FSMContext) -> None:
    delta = parse_number(message.text)
    if delta is None:
        await message.answer("Нужно число. Пример: +3 или -1.5")
        return
    await state.update_data(delta=delta)
    await state.set_state(AdjustItem.note)
    await message.answer("Комментарий (можно '-' чтобы пропустить):")


@admin_router.message(AdjustItem.note)
async def adjust_qty_note(message: Message, state: FSMContext, db: Database) -> None:
    note = message.text.strip()
    if note == "-":
        note = None
    data = await state.get_data()
    await db.adjust_item_qty(data["item_id"], data["delta"])
    await db.add_movement(data["item_id"], data["delta"], note, message.from_user.id)
    item = await db.get_item_by_id(data["item_id"])
    await state.clear()
    await message.answer(
        "Остаток обновлен.\n" + format_item_card(item),
        reply_markup=main_menu_kb(),
    )


# Установить остаток
@admin_router.message(F.text == BTN_SET_QTY)
@admin_router.callback_query(F.data == "set_qty")
async def set_qty_start(event, state: FSMContext) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event
    await state.set_state(SetQty.key)
    await message.answer("Введите SKU или ID товара:")


@admin_router.message(SetQty.key)
async def set_qty_key(message: Message, state: FSMContext, db: Database) -> None:
    item = await db.get_item_by_key(message.text)
    if not item:
        await message.answer("Товар не найден. Введите SKU или ID:")
        return
    await state.update_data(item_id=item["id"], current_qty=item["qty"])
    await state.set_state(SetQty.qty)
    await message.answer(
        f"Товар найден:\n{format_item_card(item)}\n\nВведите новый остаток (число):"
    )


@admin_router.message(SetQty.qty)
async def set_qty_value(message: Message, state: FSMContext) -> None:
    qty = parse_number(message.text)
    if qty is None:
        await message.answer("Нужно число. Пример: 10")
        return
    await state.update_data(qty=qty)
    await state.set_state(SetQty.note)
    await message.answer("Комментарий (можно '-' чтобы пропустить):")


@admin_router.message(SetQty.note)
async def set_qty_note(message: Message, state: FSMContext, db: Database) -> None:
    note = message.text.strip()
    if note == "-":
        note = None
    data = await state.get_data()
    delta = data["qty"] - data["current_qty"]
    await db.update_item_qty(data["item_id"], data["qty"])
    await db.add_movement(data["item_id"], delta, note, message.from_user.id)
    item = await db.get_item_by_id(data["item_id"])
    await state.clear()
    await message.answer(
        "Остаток установлен.\n" + format_item_card(item),
        reply_markup=main_menu_kb(),
    )


# Удалить товар
@admin_router.message(F.text == BTN_DELETE_ITEM)
@admin_router.callback_query(F.data == "delete_item")
async def delete_item_start(event, state: FSMContext) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event
    await state.set_state(DeleteItem.key)
    await message.answer("Введите SKU или ID товара для удаления:")


@admin_router.message(DeleteItem.key)
async def delete_item_key(message: Message, state: FSMContext, db: Database) -> None:
    item = await db.get_item_by_key(message.text)
    if not item:
        await message.answer("Товар не найден. Введите SKU или ID:")
        return
    await state.update_data(item_id=item["id"])
    await state.set_state(DeleteItem.confirm)
    await message.answer(
        f"Подтвердите удаление (напишите 'да'):\n{format_item_card(item)}"
    )


@admin_router.message(DeleteItem.confirm)
async def delete_item_confirm(message: Message, state: FSMContext, db: Database) -> None:
    if message.text.strip().lower() != "да":
        await message.answer("Удаление отменено.")
        await state.clear()
        return
    data = await state.get_data()
    ok = await db.delete_item(data["item_id"])
    await state.clear()
    if ok:
        await message.answer("Товар удален.", reply_markup=main_menu_kb())
    else:
        await message.answer("Не удалось удалить товар.", reply_markup=main_menu_kb())


# Поиск
@admin_router.message(F.text == BTN_SEARCH)
async def search_menu(message: Message) -> None:
    await message.answer("Выберите тип поиска:", reply_markup=search_menu_kb())


@admin_router.callback_query(F.data == "search")
async def search_start_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(SearchItem.query)
    await callback.message.answer("Введите запрос для поиска (SKU или часть названия):")


@admin_router.message(SearchItem.query)
async def search_run(message: Message, state: FSMContext, db: Database) -> None:
    query = message.text.strip()
    items = await db.search_items(query)
    await state.clear()
    if not items:
        await message.answer("Ничего не найдено.", reply_markup=main_menu_kb())
        return
    table = format_items_table(items)
    await message.answer(f"Результаты поиска:\n{table}", reply_markup=main_menu_kb())


# Список товаров
@admin_router.message(F.text == BTN_LIST_ITEMS)
async def list_items_message(message: Message, db: Database) -> None:
    text, total_pages = await render_items_page(db, 1)
    await message.answer(text, reply_markup=pagination_kb(1, total_pages))


@admin_router.callback_query(F.data.startswith("list_items:"))
async def list_items_callback(callback: CallbackQuery, db: Database) -> None:
    page = int(callback.data.split(":")[1])
    text, total_pages = await render_items_page(db, page)
    await callback.message.edit_text(
        text, reply_markup=pagination_kb(page, total_pages), parse_mode=ParseMode.HTML
    )
    await callback.answer()


# Низкие остатки
@admin_router.message(F.text == BTN_LOW_STOCK)
@admin_router.callback_query(F.data == "low_stock")
async def low_stock(event, db: Database) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event
    items = await db.list_low_stock()
    if not items:
        await message.answer("Низких остатков нет.")
        return
    table = format_items_table(items)
    await message.answer(f"Низкие остатки:\n{table}")


# Экспорт CSV
@admin_router.message(F.text == BTN_EXPORT_CSV)
@admin_router.callback_query(F.data == "export_csv")
async def export_csv(event, db: Database) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event
    items = await db.export_items()
    if not items:
        await message.answer("Склад пуст. Экспортировать нечего.")
        return
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "sku", "name", "qty", "unit", "warehouse", "location", "min_qty", "updated_at"])
    for item in items:
        writer.writerow(
            [
                item["id"],
                item["sku"],
                item["name"],
                item["qty"],
                item["unit"],
                item["warehouse"],
                item["location"],
                item["min_qty"],
                item["updated_at"],
            ]
        )
    data = output.getvalue().encode("utf-8-sig")
    await message.answer_document(
        BufferedInputFile(data, filename="stock_export.csv"),
        caption="Экспорт остатков",
    )


# История движений
@admin_router.message(F.text == BTN_HISTORY)
@admin_router.callback_query(F.data == "history")
async def history(event, db: Database) -> None:
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
    else:
        message = event
    moves = await db.list_movements()
    if not moves:
        await message.answer("История пуста.")
        return
    table = format_movements_table(moves)
    await message.answer(f"Последние движения:\n{table}")


# Настройки - обновление товара
@admin_router.callback_query(F.data == "update_item")
async def update_item_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(UpdateItem.key)
    await callback.message.answer("Введите SKU или ID товара для редактирования:")


@admin_router.callback_query(F.data == "set_min")
async def set_min_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.update_data(preset_field="min_qty")
    await state.set_state(UpdateItem.key)
    await callback.message.answer("Введите SKU или ID товара для установки мин. остатка:")


# Склады
@admin_router.callback_query(F.data == "warehouses_list")
async def warehouses_list(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    rows = await db.list_warehouses()
    if not rows:
        await callback.message.answer("Склады еще не добавлены.")
        return
    text = "Склады:\n" + "\n".join([f"- {r['name']}" for r in rows])
    await callback.message.answer(text)


@admin_router.callback_query(F.data == "warehouse_add")
async def warehouse_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AddWarehouse.name)
    await callback.message.answer("Введите название склада:")


@admin_router.message(AddWarehouse.name)
async def warehouse_add_name(message: Message, state: FSMContext, db: Database) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым.")
        return
    ok = await db.add_warehouse(name)
    await state.clear()
    if ok:
        await message.answer("Склад добавлен.", reply_markup=main_menu_kb())
    else:
        await message.answer("Такой склад уже существует.", reply_markup=main_menu_kb())


@admin_router.callback_query(F.data == "warehouse_items")
async def warehouse_items_start(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    warehouses = await db.list_warehouses()
    await callback.message.answer(
        "Выберите склад для фильтра:",
        reply_markup=warehouse_filter_kb(warehouses),
    )


@admin_router.callback_query(F.data.startswith("warehouse_filter:"))
async def warehouse_filter(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.message.answer("Неверный формат фильтра.")
        return
    warehouse_id = int(parts[1])
    sort = parts[2]
    page = int(parts[3])
    warehouse_name = None
    if warehouse_id != 0:
        wh = await db.get_warehouse_by_id(warehouse_id)
        if not wh:
            await callback.message.answer("Склад не найден.")
            return
        warehouse_name = wh["name"]
    text, total_pages = await render_items_by_warehouse(db, warehouse_name, sort, page)
    await callback.message.edit_text(
        text,
        reply_markup=warehouse_sort_kb(warehouse_id, sort, page, total_pages),
        parse_mode=ParseMode.HTML,
    )


@admin_router.message(UpdateItem.key)
async def update_item_key(message: Message, state: FSMContext, db: Database) -> None:
    item = await db.get_item_by_key(message.text)
    if not item:
        await message.answer("Товар не найден. Введите SKU или ID:")
        return
    data = await state.get_data()
    preset_field = data.get("preset_field")
    await state.update_data(item_id=item["id"])
    if preset_field:
        await state.update_data(field=preset_field)
        await state.set_state(UpdateItem.value)
        await message.answer("Введите новое значение для min_qty (число):")
        return
    await state.set_state(UpdateItem.field)
    await message.answer(
        "Выберите поле для изменения:", reply_markup=update_fields_kb()
    )


@admin_router.message(UpdateItem.field)
async def update_item_field(message: Message, state: FSMContext) -> None:
    field = message.text.strip().lower()
    if field not in {"name", "sku", "unit", "location", "warehouse", "min_qty"}:
        await message.answer("Нужно одно из: name, sku, unit, location, min_qty")
        return
    await state.update_data(field=field)
    await state.set_state(UpdateItem.value)
    await message.answer("Введите новое значение:")


@admin_router.callback_query(UpdateItem.field, F.data.startswith("update_field:"))
async def update_item_field_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    field = callback.data.split(":")[1]
    if field not in {"name", "sku", "unit", "location", "warehouse", "min_qty"}:
        await callback.message.answer("Неверное поле.")
        return
    await state.update_data(field=field)
    await state.set_state(UpdateItem.value)
    await callback.message.answer("Введите новое значение:")


@admin_router.message(UpdateItem.value)
async def update_item_value(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    field = data["field"]
    value_raw = message.text.strip()
    if field == "min_qty":
        value = parse_number(value_raw)
        if value is None:
            await message.answer("Нужно число")
            return
    elif field in {"location", "warehouse"} and value_raw == "-":
        value = None
    else:
        value = value_raw
        if not value:
            await message.answer("Значение не может быть пустым")
            return
    kwargs = {field: value}
    ok = await db.update_item_fields(data["item_id"], **kwargs)
    if not ok:
        await state.clear()
        await message.answer(
            "Не удалось обновить данные (возможно, SKU уже существует).",
            reply_markup=main_menu_kb(),
        )
        return
    item = await db.get_item_by_id(data["item_id"])
    await state.clear()
    await message.answer(
        "Данные обновлены.\n" + format_item_card(item),
        reply_markup=main_menu_kb(),
    )


# Админ-панель
@admin_router.callback_query(F.data == "admins_list")
async def admins_list(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    admins = await db.list_admins()
    lines = ["Админы:"]
    for adm in admins:
        lines.append(f"- {adm['tg_id']} ({adm['name'] or '-'})")
    await callback.message.answer("\n".join(lines))


@admin_router.callback_query(F.data == "admin_add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext, config) -> None:
    await callback.answer()
    if not is_super_admin(callback.from_user.id, config):
        await callback.message.answer("Недостаточно прав для управления админами.")
        return
    await state.set_state(AddAdmin.tg_id)
    await callback.message.answer("Введите Telegram ID нового админа:")


@admin_router.message(AddAdmin.tg_id)
async def admin_add_tg_id(message: Message, state: FSMContext, config) -> None:
    if not is_super_admin(message.from_user.id, config):
        await state.clear()
        await message.answer("Недостаточно прав для управления админами.")
        return
    if not message.text.strip().isdigit():
        await message.answer("Нужен числовой ID")
        return
    await state.update_data(tg_id=int(message.text.strip()))
    await state.set_state(AddAdmin.name)
    await message.answer("Имя/комментарий (можно '-'): ")


@admin_router.message(AddAdmin.name)
async def admin_add_name(message: Message, state: FSMContext, db: Database, config) -> None:
    if not is_super_admin(message.from_user.id, config):
        await state.clear()
        await message.answer("Недостаточно прав для управления админами.")
        return
    name = message.text.strip()
    if name == "-":
        name = None
    data = await state.get_data()
    ok = await db.add_admin(data["tg_id"], name)
    await state.clear()
    if ok:
        await message.answer("Админ добавлен.", reply_markup=main_menu_kb())
    else:
        await message.answer("Админ уже существует.", reply_markup=main_menu_kb())


@admin_router.callback_query(F.data == "admin_remove")
async def admin_remove_start(callback: CallbackQuery, state: FSMContext, config) -> None:
    await callback.answer()
    if not is_super_admin(callback.from_user.id, config):
        await callback.message.answer("Недостаточно прав для управления админами.")
        return
    await state.set_state(RemoveAdmin.tg_id)
    await callback.message.answer("Введите Telegram ID для удаления из админов:")


@admin_router.message(RemoveAdmin.tg_id)
async def admin_remove_tg_id(message: Message, state: FSMContext, db: Database, config) -> None:
    if not is_super_admin(message.from_user.id, config):
        await state.clear()
        await message.answer("Недостаточно прав для управления админами.")
        return
    if not message.text.strip().isdigit():
        await message.answer("Нужен числовой ID")
        return
    tg_id = int(message.text.strip())
    ok = await db.remove_admin(tg_id)
    await state.clear()
    if ok:
        await message.answer("Админ удален.", reply_markup=main_menu_kb())
    else:
        await message.answer("Админ не найден.", reply_markup=main_menu_kb())


@admin_router.callback_query(F.data == "backup_db")
async def backup_db(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    if not db.path:
        await callback.message.answer("Путь к БД не задан.")
        return
    if not os.path.exists(db.path):
        await callback.message.answer("Файл БД не найден.")
        return
    await callback.message.answer_document(
        FSInputFile(db.path, filename="warehouse.db"),
        caption="Резервная копия БД",
    )


@admin_router.message(BulkAdd.lines)
async def bulk_add_process(message: Message, state: FSMContext, db: Database) -> None:
    rows = parse_bulk_lines(message.text or "")
    if not rows:
        await message.answer("Список пуст. Пришлите строки по формату CSV.")
        return

    created = 0
    skipped = 0
    errors: list[str] = []

    for idx, row in enumerate(rows, start=1):
        sku = row[0].strip() if len(row) > 0 else ""
        name = row[1].strip() if len(row) > 1 else ""
        qty_raw = row[2].strip() if len(row) > 2 else ""
        unit = row[3].strip() if len(row) > 3 and row[3].strip() else "шт"
        location = row[4].strip() if len(row) > 4 else ""
        warehouse = row[5].strip() if len(row) > 5 else ""
        min_qty_raw = row[6].strip() if len(row) > 6 else "0"

        if not sku or not name or not qty_raw:
            errors.append(f"Строка {idx}: нужно sku,name,qty")
            continue
        qty = parse_number(qty_raw)
        if qty is None:
            errors.append(f"Строка {idx}: неверный qty")
            continue
        min_qty = parse_number(min_qty_raw)
        if min_qty is None:
            errors.append(f"Строка {idx}: неверный min_qty")
            continue
        location = location or None
        warehouse = warehouse or None

        if warehouse:
            wh = await db.get_warehouse_by_name(warehouse)
            if not wh:
                await db.add_warehouse(warehouse)

        ok = await db.add_item(
            sku=sku,
            name=name,
            qty=qty,
            unit=unit,
            location=location,
            warehouse=warehouse,
            min_qty=min_qty,
        )
        if ok:
            created += 1
        else:
            skipped += 1
            errors.append(f"Строка {idx}: SKU уже существует")

    await state.clear()
    summary = [
        f"Готово. Добавлено: {created}. Пропущено: {skipped}.",
    ]
    if errors:
        summary.append("Ошибки:")
        summary.extend(errors[:10])
        if len(errors) > 10:
            summary.append(f"... еще {len(errors) - 10}")
    await message.answer("\n".join(summary), reply_markup=main_menu_kb())


@admin_router.message()
async def admin_unknown(message: Message, state: FSMContext) -> None:
    logger.info(
        "Unhandled admin message. user_id=%s text=%r state=%s",
        message.from_user.id,
        message.text,
        await state.get_state(),
    )
    await message.answer("Не понял команду. Используйте меню.", reply_markup=main_menu_kb())


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config = load_config()
    logger.info("Loaded config. SUPERADMINS=%s DB_PATH=%s", sorted(config.super_admins), config.db_path)
    db = Database(config.db_path)
    await db.init()
    if config.super_admins:
        await db.ensure_admins(config.super_admins)
        logger.info("Ensured superadmins in DB.")

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbMiddleware(db))
    dp.update.middleware(ConfigMiddleware(config))
    dp.include_router(admin_router)
    dp.include_router(public_router)

    try:
        logger.info("Bot started. Polling...")
        await dp.start_polling(bot)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
