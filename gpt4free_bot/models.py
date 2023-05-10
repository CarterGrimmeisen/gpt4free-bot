from playhouse.sqlite_ext import SqliteExtDatabase, Model, TextField, IntegerField
from typing import TypedDict

db = SqliteExtDatabase(
    "settings.db",
    pragmas={
        "journal_mode": "wal",
        "cache_size": -1024 * 64,
    },
)


class Base(Model):
    class Meta:
        database = db


class Settings(Base):
    guild = TextField(primary_key=True)
    persona = TextField(default="")
    context_message_count = IntegerField(default=5)


class SettingsDict(TypedDict):
    guild: str
    persona: str
    context_message_count: int


DEFAULT_SETTINGS = SettingsDict(guild="", persona="", context_message_count=5)
