from aiogram.filters import Filter
from aiogram.types import TelegramObject

from db import Database


class IsAdmin(Filter):
    async def __call__(self, event: TelegramObject, db: Database) -> bool:
        user = getattr(event, "from_user", None)
        if not user:
            return False
        return await db.is_admin(user.id)
