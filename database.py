import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_PATH = "bot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                keywords TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY
            )
        """)
        await db.commit()


async def add_source(user_id: int, name: str, url: str, keywords: list[str]) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO user_sources (user_id, name, url, keywords) VALUES (?, ?, ?, ?)",
            (user_id, name, url, ",".join(keywords)),
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_sources(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, name, url, keywords FROM user_sources WHERE user_id = ? ORDER BY id",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "url": r["url"],
                "keywords": r["keywords"].split(","),
                "check_type": "keyword",
            }
            for r in rows
        ]


async def get_all_user_sources() -> dict[int, list[dict]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, user_id, name, url, keywords FROM user_sources ORDER BY user_id"
        )
        rows = await cursor.fetchall()
        result = {}
        for r in rows:
            uid = r["user_id"]
            if uid not in result:
                result[uid] = []
            result[uid].append({
                "id": r["id"],
                "name": r["name"],
                "url": r["url"],
                "keywords": r["keywords"].split(","),
                "check_type": "keyword",
            })
        return result


async def remove_source(source_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM user_sources WHERE id = ? AND user_id = ?",
            (source_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def add_subscriber(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)", (user_id,)
        )
        await db.commit()


async def get_subscribers() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM subscribers")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]
