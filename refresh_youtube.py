"""
Локальный скрипт: открывает браузер → логин в YouTube → печатает JSON кук.
Скопируй вывод (весь JSON) и отправь боту: /ytcookies <вставь JSON>

Требует: pip install playwright && python -m playwright install chromium
"""

import asyncio
import json

from playwright.async_api import async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

async def main():
    print("=" * 60)
    print("  Запускаю браузер...")
    print("=" * 60)

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False)
    ctx = await browser.new_context(
        viewport={"width": 1366, "height": 768},
        user_agent=USER_AGENT,
        locale="en-US",
    )
    page = await ctx.new_page()

    try:
        await page.goto("https://www.youtube.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        print("\n" + "=" * 60)
        print("  🌐 ВОЙДИ В АККАУНТ YOUTUBE в открывшемся браузере")
        print("  После входа нажми Enter здесь (в терминале)")
        print("=" * 60)
        input("  ▶  Нажми Enter после входа...  ")

        await page.wait_for_timeout(3000)

        # Navigate to youtube.com/upload to ensure session is set
        await page.goto("https://www.youtube.com/upload", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        cookies = await ctx.cookies()
        json_str = json.dumps(cookies, indent=2, default=str)

        print("\n" + "=" * 60)
        print(f"  ✅ Куки получены ({len(cookies)} шт)")
        print("  Скопируй JSON ниже и отправь боту:")
        print()
        print("  /ytcookies <вставь весь JSON>")
        print()
        print("  Или сохрани в файл и отправь как документ")
        print("=" * 60)
        print()
        print(json_str)

        # Also save to file as fallback
        with open("youtube_cookies_fresh.json", "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"\n  💾 Сохранено в youtube_cookies_fresh.json")
        print(f"  📎 Отправь этот файл боту как документ")

    finally:
        await browser.close()
        await pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
