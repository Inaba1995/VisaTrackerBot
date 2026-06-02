import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "10"))

VISA_SOURCES = [
    {
        "name": "VFS Italy Moscow",
        "url": "https://visa.vfsglobal.com/rus/ru/ita/book-an-appointment",
        "check_type": "keyword",
        "keywords": ["есть", "доступно", "свободно", "available", "appointment"],
    },
    {
        "name": "Italy Visa Appointment",
        "url": "https://prenotami.eu/",
        "check_type": "keyword",
        "keywords": ["slot", "available", "disponibile"],
    },
]
