import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.enums import ParseMode

from config import BOT_TOKEN, CHECK_INTERVAL_MINUTES, VISA_SOURCES
from scraper import check_all_sources

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

user_ids = set()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_ids.add(message.from_user.id)
    await message.answer(
        "🇮🇹 <b>Visa Tracker Bot</b>\n\n"
        "Я отслеживаю появление слотов для записи на визу в Италию.\n\n"
        "Команды:\n"
        "/check — проверить прямо сейчас\n"
        "/sources — список отслеживаемых источников\n"
        "/interval — интервал проверки\n"
        "/subscribe — подписаться на уведомления\n"
        "/help — помощь"
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await cmd_start(message)


@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    await message.answer("🔍 Проверяю источники...")
    hits = await check_all_sources()
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
    text = "📋 <b>Отслеживаемые источники:</b>\n\n" + "\n".join(
        f"• {s['name']}\n  <code>{s['url']}</code>" for s in VISA_SOURCES
    )
    await message.answer(text)


@dp.message(Command("subscribe"))
async def cmd_subscribe(message: types.Message):
    user_ids.add(message.from_user.id)
    await message.answer("✅ Ты подписан на уведомления. Я буду писать, когда появятся слоты.")


@dp.message(Command("interval"))
async def cmd_interval(message: types.Message):
    await message.answer(f"⏱ Интервал проверки: каждые {CHECK_INTERVAL_MINUTES} мин.")


async def periodic_check():
    while True:
        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)
        if not user_ids:
            continue
        logger.info("Periodic check: %d subscribers", len(user_ids))
        hits = await check_all_sources()
        if hits:
            for user_id in user_ids:
                for h in hits:
                    try:
                        msg = (
                            f"🚨 <b>Слоты появились!</b>\n"
                            f"Источник: {h['source']}\n"
                            f"<a href='{h['url']}'>Записаться</a>"
                        )
                        await bot.send_message(user_id, msg)
                    except Exception as e:
                        logger.warning("Failed to notify %s: %s", user_id, e)


async def main():
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token":
        logger.error("BOT_TOKEN not set!")
        return

    asyncio.create_task(periodic_check())
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
