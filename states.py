from aiogram.fsm.state import State, StatesGroup


class AddItem(StatesGroup):
    sku = State()
    name = State()
    qty = State()
    unit = State()
    location = State()
    warehouse = State()
    min_qty = State()


class AdjustItem(StatesGroup):
    key = State()
    delta = State()
    note = State()


class SetQty(StatesGroup):
    key = State()
    qty = State()
    note = State()


class DeleteItem(StatesGroup):
    key = State()
    confirm = State()


class UpdateItem(StatesGroup):
    key = State()
    field = State()
    value = State()


class SearchItem(StatesGroup):
    query = State()


class AddAdmin(StatesGroup):
    tg_id = State()
    name = State()


class RemoveAdmin(StatesGroup):
    tg_id = State()


class AddWarehouse(StatesGroup):
    name = State()


class BulkAdd(StatesGroup):
    lines = State()
