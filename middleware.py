from aiogram import BaseMiddleware

from config import Config
from db import Database


class DbMiddleware(BaseMiddleware):
    def __init__(self, db: Database) -> None:
        self.db = db

    async def __call__(self, handler, event, data):
        data["db"] = self.db
        return await handler(event, data)


class ConfigMiddleware(BaseMiddleware):
    def __init__(self, config: Config) -> None:
        self.config = config

    async def __call__(self, handler, event, data):
        data["config"] = self.config
        return await handler(event, data)
