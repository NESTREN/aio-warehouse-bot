from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from constants import (
    BTN_ADD_ITEM,
    BTN_ADMIN,
    BTN_ADJUST_QTY,
    BTN_BACK,
    BTN_BULK_ADD,
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


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=BTN_WAREHOUSE),
                KeyboardButton(text=BTN_REPORTS),
                KeyboardButton(text=BTN_ADMIN),
            ],
            [
                KeyboardButton(text=BTN_ADD_ITEM),
                KeyboardButton(text=BTN_ADJUST_QTY),
                KeyboardButton(text=BTN_LIST_ITEMS),
            ],
            [
                KeyboardButton(text=BTN_BULK_ADD),
            ],
            [
                KeyboardButton(text=BTN_SEARCH),
                KeyboardButton(text=BTN_LOW_STOCK),
                KeyboardButton(text=BTN_EXPORT_CSV),
            ],
            [
                KeyboardButton(text=BTN_HISTORY),
                KeyboardButton(text=BTN_SETTINGS),
                KeyboardButton(text=BTN_HELP),
            ],
            [
                KeyboardButton(text=BTN_WAREHOUSES),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие из меню ниже",
    )


def warehouse_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=BTN_ADD_ITEM, callback_data="add_item"),
                InlineKeyboardButton(text=BTN_ADJUST_QTY, callback_data="adjust_qty"),
            ],
            [
                InlineKeyboardButton(text=BTN_BULK_ADD, callback_data="bulk_add"),
                InlineKeyboardButton(text=BTN_SET_QTY, callback_data="set_qty"),
                InlineKeyboardButton(text=BTN_DELETE_ITEM, callback_data="delete_item"),
            ],
            [
                InlineKeyboardButton(text=BTN_LIST_ITEMS, callback_data="list_items:1"),
                InlineKeyboardButton(text=BTN_SEARCH, callback_data="search"),
            ],
            [
                InlineKeyboardButton(text=BTN_LOW_STOCK, callback_data="low_stock"),
                InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main"),
            ],
        ]
    )


def reports_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=BTN_EXPORT_CSV, callback_data="export_csv"),
                InlineKeyboardButton(text=BTN_HISTORY, callback_data="history"),
            ],
            [
                InlineKeyboardButton(text=BTN_LOW_STOCK, callback_data="low_stock"),
                InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main"),
            ],
        ]
    )


def search_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Поиск товара", callback_data="search"),
                InlineKeyboardButton(text="По складу", callback_data="warehouse_items"),
            ],
            [
                InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main"),
            ],
        ]
    )


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Список админов", callback_data="admins_list"),
                InlineKeyboardButton(text="Добавить админа", callback_data="admin_add"),
            ],
            [
                InlineKeyboardButton(text="Удалить админа", callback_data="admin_remove"),
                InlineKeyboardButton(text="Резервная копия БД", callback_data="backup_db"),
            ],
            [
                InlineKeyboardButton(text=BTN_WAREHOUSES, callback_data="warehouses_menu"),
                InlineKeyboardButton(text=BTN_SETTINGS, callback_data="settings_menu"),
            ],
            [
                InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main"),
            ],
        ]
    )


def settings_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Обновить данные товара", callback_data="update_item"),
                InlineKeyboardButton(text="Установить мин. остаток", callback_data="set_min"),
            ],
            [
                InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main"),
            ],
        ]
    )


def warehouses_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Список складов", callback_data="warehouses_list"),
                InlineKeyboardButton(text="Добавить склад", callback_data="warehouse_add"),
            ],
            [
                InlineKeyboardButton(text="Товары по складу", callback_data="warehouse_items"),
            ],
            [
                InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main"),
            ],
        ]
    )


def warehouses_select_kb(warehouses: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for row in warehouses:
        rows.append(
            [InlineKeyboardButton(text=row["name"], callback_data=f"warehouse_select:{row['id']}")]
        )
    rows.append([InlineKeyboardButton(text="Пропустить", callback_data="warehouse_select:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def warehouse_filter_kb(warehouses: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for row in warehouses:
        rows.append(
            [InlineKeyboardButton(text=row["name"], callback_data=f"warehouse_filter:{row['id']}:name:1")]
        )
    rows.append([InlineKeyboardButton(text="Все склады", callback_data="warehouse_filter:0:name:1")])
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def warehouse_sort_kb(warehouse_id: int, sort: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="Сорт: Название" + (" ✅" if sort == "name" else ""),
                callback_data=f"warehouse_filter:{warehouse_id}:name:{page}",
            ),
            InlineKeyboardButton(
                text="Сорт: Остаток" + (" ✅" if sort == "qty" else ""),
                callback_data=f"warehouse_filter:{warehouse_id}:qty:{page}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Сорт: SKU" + (" ✅" if sort == "sku" else ""),
                callback_data=f"warehouse_filter:{warehouse_id}:sku:{page}",
            ),
        ],
    ]
    nav = []
    if page > 1:
        nav.append(
            InlineKeyboardButton(
                text="Назад", callback_data=f"warehouse_filter:{warehouse_id}:{sort}:{page - 1}"
            )
        )
    if page < total_pages:
        nav.append(
            InlineKeyboardButton(
                text="Вперед", callback_data=f"warehouse_filter:{warehouse_id}:{sort}:{page + 1}"
            )
        )
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def update_fields_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Название", callback_data="update_field:name"),
                InlineKeyboardButton(text="SKU", callback_data="update_field:sku"),
            ],
            [
                InlineKeyboardButton(text="Ед. изм.", callback_data="update_field:unit"),
                InlineKeyboardButton(text="Локация", callback_data="update_field:location"),
            ],
            [
                InlineKeyboardButton(text="Мин. остаток", callback_data="update_field:min_qty"),
                InlineKeyboardButton(text="Склад", callback_data="update_field:warehouse"),
            ],
            [
                InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main"),
            ],
        ]
    )


def pagination_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    if page > 1:
        buttons.append(
            InlineKeyboardButton(text="Назад", callback_data=f"list_items:{page - 1}")
        )
    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(text="Вперед", callback_data=f"list_items:{page + 1}")
        )
    buttons.append(InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_main")]
        ]
    )
