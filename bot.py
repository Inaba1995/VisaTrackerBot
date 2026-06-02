import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.enums import ParseMode

from config import BOT_TOKEN, CHECK_INTERVAL_MINUTES, VISA_SOURCES
from scraper import check_all_sources
from database import (
    init_db,
    add_source,
    get_user_sources,
    get_all_user_sources,
    remove_source,
    add_subscriber,
    get_subscribers,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await add_subscriber(message.from_user.id)
    await message.answer(
        "🇮🇹 <b>Visa Tracker Bot</b>\n\n"
        "Я отслеживаю появление слотов для записи на визу в Италию.\n\n"
        "Команды:\n"
        "/check — проверить прямо сейчас\n"
        "/sources — список общих источников\n"
        "/addsource &lt;url&gt; &lt;слова&gt; — добавить свой источник\n"
        "/mysources — мои источники\n"
        "/removesource &lt;id&gt; — удалить мой источник\n"
        "/subscribe — подписаться на уведомления\n"
        "/interval — интервал проверки\n"
        "/help — помощь"
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await cmd_start(message)


@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    await message.answer("🔍 Проверяю источники...")
    user_sources = await get_all_user_sources()
    hits = await check_all_sources(user_sources)
    if hits:
        for h in hits:
            msg = (
                f"✅ <b>Найдено в {h['source']}</b>\n"
                f"Ключевые слова: {', '.join(h['found_keywords'])}\n"
                f"<a href='{h['url']}'>Перейти</a>"
            )
            await message.answer(msg)
    else:
        await message.answer("❌ Слотов пока нет. Попробую позже.")


@dp.message(Command("sources"))
async def cmd_sources(message: types.Message):
    text = "📋 <b>Общие источники:</b>\n\n" + "\n".join(
        f"• {s['name']}\n  <code>{s['url']}</code>" for s in VISA_SOURCES
    )
    await message.answer(text)


@dp.message(Command("subscribe"))
async def cmd_subscribe(message: types.Message):
    await add_subscriber(message.from_user.id)
    await message.answer("✅ Ты подписан на уведомления. Я буду писать, когда появятся слоты.")


@dp.message(Command("interval"))
async def cmd_interval(message: types.Message):
    await message.answer(f"⏱ Интервал проверки: каждые {CHECK_INTERVAL_MINUTES} мин.")


@dp.message(Command("addsource"))
async def cmd_addsource(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "❌ Использование: /addsource &lt;url&gt; &lt;ключевые слова через запятую&gt;\n\n"
            "Пример: /addsource https://example.com свободно,доступно,slot"
        )
        return
    url = args[1]
    keywords = [kw.strip() for kw in args[2].split(",") if kw.strip()]
    if not keywords:
        await message.answer("❌ Укажи хотя бы одно ключевое слово.")
        return
    name = url.replace("https://", "").replace("http://", "").split("/")[0]
    source_id = await add_source(message.from_user.id, name, url, keywords)
    await message.answer(
        f"✅ Источник <b>{name}</b> добавлен!\n"
        f"ID: {source_id}\n"
        f"Ключевые слова: {', '.join(keywords)}"
    )


@dp.message(Command("mysources"))
async def cmd_mysources(message: types.Message):
    sources = await get_user_sources(message.from_user.id)
    if not sources:
        await message.answer("📭 У тебя нет добавленных источников.\nИспользуй /addsource чтобы добавить.")
        return
    lines = ["📋 <b>Твои источники:</b>\n"]
    for s in sources:
        lines.append(
            f"<b>ID {s['id']}</b>: {s['name']}\n"
            f"  <code>{s['url']}</code>\n"
            f"  Слова: {', '.join(s['keywords'])}"
        )
    await message.answer("\n\n".join(lines))


@dp.message(Command("removesource"))
async def cmd_removesource(message: types.Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❌ Использование: /removesource &lt;id&gt;\nУзнать ID можно через /mysources")
        return
    source_id = int(args[1])
    ok = await remove_source(source_id, message.from_user.id)
    if ok:
        await message.answer(f"✅ Источник ID {source_id} удалён.")
    else:
        await message.answer(f"❌ Источник ID {source_id} не найден или это не твой источник.")


async def periodic_check():
    while True:
        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)
        subscribers = await get_subscribers()
        if not subscribers:
            continue
        logger.info("Periodic check: %d subscribers", len(subscribers))
        user_sources = await get_all_user_sources()
        hits = await check_all_sources(user_sources)
        if hits:
            for h in hits:
                user_id = h.get("user_id")
                if user_id:
                    try:
                        msg = (
                            f"🚨 <b>Слоты в твоём источнике!</b>\n"
                            f"Источник: {h['source']}\n"
                            f"<a href='{h['url']}'>Перейти</a>"
                        )
                        await bot.send_message(user_id, msg)
                    except Exception as e:
                        logger.warning("Failed to notify %s: %s", user_id, e)
                else:
                    for uid in subscribers:
                        try:
                            msg = (
                                f"🚨 <b>Слоты появились!</b>\n"
                                f"Источник: {h['source']}\n"
                                f"<a href='{h['url']}'>Записаться</a>"
                            )
                            await bot.send_message(uid, msg)
                        except Exception as e:
                            logger.warning("Failed to notify %s: %s", uid, e)


async def run_web_server():
    port = int(os.getenv("PORT", "10000"))
    from aiohttp import web
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health check server running on port %d", port)


async def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token":
        logger.error("BOT_TOKEN not set!")
        return

    await init_db()
    asyncio.create_task(run_web_server())
    asyncio.create_task(periodic_check())
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
