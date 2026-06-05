"""
Запусти — откроется браузер, залогинься в YouTube, нажми Enter.
Куки сохранятся в youtube_cookies/youtube_cookies.json.
"""

import asyncio
import logging

from youtube_uploader import YouTubeUploader

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

async def main():
    up = YouTubeUploader(headless=False)
    ok = await up.login()
    if ok:
        print("\n✅ Куки сохранены. Можно запускать загрузку видео.")
    else:
        print("\n❌ Ошибка входа.")

if __name__ == "__main__":
    asyncio.run(main())
