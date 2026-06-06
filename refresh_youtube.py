"""
Local script: launches your real Chrome → exports YouTube cookies.
You're already logged into YouTube in Chrome — no re-login needed!

Copy the JSON output and send to bot: /ytcookies <paste JSON>
Or send the file youtube_cookies_fresh.json as a document.

Requires: pip install playwright  (no browser install needed — uses system Chrome)
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright


async def main():
    # Find system Chrome on Windows
    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    chrome_path = None
    for p in chrome_candidates:
        if Path(p).exists():
            chrome_path = str(p)
            break

    print("=" * 60)
    print("  Launching your real Chrome (where you're logged into YouTube)...")
    if chrome_path:
        print(f"  Found: {chrome_path}")
    print("=" * 60)

    pw = await async_playwright().start()

    # Use system Chrome with its default profile — you're already logged in
    launch_opts = {
        "headless": False,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
        ],
    }
    if chrome_path:
        launch_opts["executable_path"] = chrome_path

    browser = await pw.chromium.launch(**launch_opts)

    # Reuse the existing default context (has your profile/session)
    if browser.contexts:
        ctx = browser.contexts[0]
    else:
        ctx = await browser.new_context(viewport={"width": 1366, "height": 768})

    page = await ctx.new_page()

    try:
        await page.goto("https://www.youtube.com/upload", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        if "signin" in page.url.lower() or "accounts" in page.url.lower():
            print("\n" + "=" * 60)
            print("  ❌ NOT logged in. Login in the browser window,")
            print("     then press Enter here.")
            print("=" * 60)
            input("  ▶  Press Enter after login...  ")
            await page.wait_for_timeout(3000)
        else:
            print("  ✅ Already logged in! Extracting cookies...")

        cookies = await ctx.cookies()
        json_str = json.dumps(cookies, indent=2, default=str)

        print("\n" + "=" * 60)
        print(f"  ✅ Got {len(cookies)} cookies")
        print()
        print("  Send to bot:")
        print()
        print("    /ytcookies <paste the ENTIRE JSON>")
        print()
        print("  Or send youtube_cookies_fresh.json as a document")
        print("=" * 60, end="\n\n")

        # Show first 2000 chars
        print(json_str[:2000])
        if len(json_str) > 2000:
            print(f"\n  ... ({len(json_str) - 2000} more chars — full JSON saved to file)")

        # Save full JSON to file
        with open("youtube_cookies_fresh.json", "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"\n  💾 Saved to: youtube_cookies_fresh.json")
        print(f"  📎 Send this file to the bot as a document")

    finally:
        try:
            await browser.close()
        except:
            pass
        await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
