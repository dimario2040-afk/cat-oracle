"""
Запусти — откроется браузер, залогинься в YouTube, нажми Enter.
Куки сохранятся локально в youtube_cookies/youtube_cookies.json.

После входа:
  1. Открой youtube_cookies/youtube_cookies.json
  2. Скопируй всё содержимое (весь JSON)
  3. Отправь боту: /ytcookies <вставь скопированный JSON>
"""

import asyncio
import json
import logging
from pathlib import Path

from youtube_uploader import YouTubeUploader

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

async def main():
    up = YouTubeUploader(headless=False)
    ok = await up.login()
    if ok:
        path = Path("youtube_cookies") / "youtube_cookies.json"
        size = len(json.loads(path.read_text(encoding="utf-8")))
        print(f"\n✅ Куки сохранены ({size} шт)")
        print(f"   Файл: {path}")
        print(f"\n📋 Отправь файл {path} боту (как документ)")
        print(f"   Или отправь команду: /ytcookies <содержимое {path.name}>")
    else:
        print("\n❌ Ошибка входа.")

if __name__ == "__main__":
    asyncio.run(main())
