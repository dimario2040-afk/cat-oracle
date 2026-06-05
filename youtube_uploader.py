"""
YouTube Shorts uploader via Playwright (browser automation).
No API key needed — uses YouTube Studio login cookies.

Usage:
    # STEP 1 – Login (once, interactive)
    python login_youtube.py

    # STEP 2 – Upload
    from youtube_uploader import YouTubeUploader
    up = YouTubeUploader()
    await up.upload_short("video.mp4", "My Totem", "My description")
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

logger = logging.getLogger("youtube_uploader")

COOKIES_DIR = Path("youtube_cookies")
COOKIES_PATH = COOKIES_DIR / "youtube_cookies.json"

# ── helpers ──────────────────────────────────────────────────────────

LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-web-security",
    "--disable-features=IsolateOrigins,site-per-process",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ── uploader ─────────────────────────────────────────────────────────

class YouTubeUploader:
    """Upload Shorts to YouTube via automated YouTube Studio workflow."""

    def __init__(self, cookies_path: str | Path | None = None, headless: bool = True):
        self.cookies_path = Path(cookies_path or COOKIES_PATH)
        self.headless = headless

    # ── context factory ──────────────────────────────────────────────

    async def _browser(self):
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=self.headless, args=LAUNCH_ARGS)
        ctx = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=USER_AGENT,
            locale="en-US",
        )
        if self.cookies_path.exists():
            with open(self.cookies_path) as f:
                await ctx.add_cookies(json.load(f))
        return pw, browser, ctx

    # ── interactive login ────────────────────────────────────────────

    async def login(self):
        """Open headed browser → user logs into YouTube → cookies saved."""
        COOKIES_DIR.mkdir(parents=True, exist_ok=True)
        pw, browser, ctx = await self._browser()
        page = await ctx.new_page()
        try:
            await page.goto("https://studio.youtube.com", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            print("\n" + "=" * 60)
            print("  ВОЙДИ В АККАУНТ YOUTUBE в открывшемся браузере")
            print("  После входа нажми Enter здесь (в терминале)")
            print("=" * 60)
            input("  ▶  Нажми Enter после входа...")

            await page.wait_for_timeout(3000)
            cookies = await ctx.cookies()
            with open(self.cookies_path, "w") as f:
                json.dump(cookies, f, indent=2, default=str)
            logger.info(f"Cookies saved: {self.cookies_path} ({len(cookies)} шт)")
            return True
        finally:
            await browser.close()
            await pw.stop()

    # ── upload ───────────────────────────────────────────────────────

    async def upload_short(
        self,
        mp4_path: str | Path,
        title: str,
        description: str = "",
        visibility: str = "unlisted",
    ) -> bool:
        """
        Upload a video to YouTube as a Short.

        Parameters
        ----------
        mp4_path : path to the .mp4 file
        title : video title
        description : description text (#Shorts added automatically)
        visibility : "public" | "unlisted" | "private"

        Returns True on success.
        """
        mp4_path = Path(mp4_path)
        if not mp4_path.is_file():
            raise FileNotFoundError(f"Video not found: {mp4_path}")
        if not self.cookies_path.exists():
            raise RuntimeError(
                "Not logged in. Run login() or use login_youtube.py first."
            )

        # Ensure #Shorts in description
        desc = description.strip()
        if "#Shorts" not in desc and "#shorts" not in desc:
            desc += "\n\n#Shorts"

        pw, browser, ctx = await self._browser()
        page = await ctx.new_page()
        try:
            # ── goto Studio ──
            logger.info("Opening YouTube Studio…")
            await page.goto(
                "https://studio.youtube.com", wait_until="domcontentloaded", timeout=30000
            )
            await page.wait_for_load_state("networkidle")

            # Detect redirect to login
            if "signin" in page.url.lower() or "accounts" in page.url.lower():
                logger.error("Session expired — run login_youtube.py again")
                await page.screenshot(path="youtube_session_expired.png")
                return False

            # ── click CREATE ──
            logger.info("Clicking CREATE…")
            create_btn = page.get_by_role("button", name="CREATE", exact=True)
            # fallback: also try the icon button
            if not await create_btn.is_visible():
                create_btn = page.locator("#create-icon")
            await create_btn.first.wait_for(timeout=15000)
            await create_btn.first.click()
            await page.wait_for_timeout(1500)

            # ── choose "Upload videos" ──
            await page.get_by_text("Upload videos", exact=True).click()
            await page.wait_for_timeout(2000)

            # ── file picker ──
            logger.info(f"Uploading {mp4_path.name}…")
            async with page.expect_file_chooser(timeout=15000) as fc_info:
                select_btn = page.get_by_text("Select files")
                if await select_btn.is_visible():
                    await select_btn.click()
                else:
                    # fallback: click the drop zone
                    await page.locator("#upload-drop-zone").click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(str(mp4_path.resolve()))

            # ── wait for processing ──
            logger.info("Waiting for upload processing…")
            title_box = page.locator("#title-text")
            await title_box.wait_for(timeout=180_000)  # 3 min for processing
            await page.wait_for_timeout(2000)

            # ── fill title ──
            await title_box.click()
            await title_box.fill(title[:100])  # YT limit 100 chars

            # ── fill description ──
            desc_box = page.locator("#description-text")
            await desc_box.click()
            await desc_box.fill(desc)

            # ── NEXT × 3 ──
            for step_name in ("Details", "Video elements", "Visibility"):
                logger.info(f"Next → {step_name}")
                next_btn = page.get_by_role("button", name="Next", exact=True)
                await next_btn.wait_for(timeout=10000)
                await next_btn.click()
                await page.wait_for_timeout(2500)

            # ── visibility ──
            v_key = visibility.upper()
            if v_key not in ("PUBLIC", "UNLISTED", "PRIVATE"):
                v_key = "UNLISTED"
            radio = page.get_by_role("radio", name=v_key)
            await radio.scroll_into_view_if_needed()
            await radio.click()
            await page.wait_for_timeout(500)

            # ── PUBLISH ──
            logger.info("Publishing…")
            publish = page.get_by_role("button", name="Publish", exact=True)
            await publish.wait_for(timeout=10000)
            await publish.click()

            await page.wait_for_timeout(5000)
            logger.info(f"✅ Published: {title}")
            return True

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            try:
                await page.screenshot(path="youtube_upload_error.png")
                logger.info("Screenshot saved to youtube_upload_error.png")
            except Exception:
                pass
            return False
        finally:
            await browser.close()
            await pw.stop()


# ── direct call ──────────────────────────────────────────────────────

async def upload_video(mp4_path: str, title: str, description: str = "",
                       visibility: str = "unlisted") -> bool:
    """Shortcut: create uploader and upload in one call."""
    up = YouTubeUploader()
    return await up.upload_short(mp4_path, title, description, visibility)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    if len(sys.argv) < 3:
        print("Usage: python youtube_uploader.py <video.mp4> <title> [description] [public|unlisted|private]")
        sys.exit(1)
    mp4 = sys.argv[1]
    title = sys.argv[2]
    desc = sys.argv[3] if len(sys.argv) > 3 else ""
    vis = sys.argv[4] if len(sys.argv) > 4 else "unlisted"
    asyncio.run(upload_video(mp4, title, desc, vis))
