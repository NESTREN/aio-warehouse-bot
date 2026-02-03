import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class Config:
    bot_token: str
    db_path: str
    super_admins: set[int]


def load_config() -> Config:
    env_path = Path(__file__).with_name(".env")
    load_dotenv(env_path, override=True)
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is required in .env")
    db_path = os.getenv("DB_PATH", "data.db").strip() or "data.db"
    raw_admins = os.getenv("SUPERADMINS", "").strip()
    super_admins: set[int] = set()
    if raw_admins:
        for part in raw_admins.replace(" ", "").split(","):
            if part:
                super_admins.add(int(part))
    return Config(bot_token=token, db_path=db_path, super_admins=super_admins)
