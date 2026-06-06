"""
Local YouTube Shorts uploader for CatWood Bot.

HOW IT WORKS:
1. Bot sends totem video to admin chat with #youtube_upload caption
2. This script detects the video via Telethon (admin Telegram session)
3. Extracts YouTube cookies from your Chrome browser
4. Uses Playwright to inject cookies and upload to YouTube Studio
5. Fills title/description/visibility from caption

SETUP:
1. pip install telethon playwright browser-cookie3
2. playwright install chromium
3. Get API_ID and API_HASH from https://my.telegram.org
4. python local_yt_uploader.py  (first run = login via phone)

DEPENDENCIES:
   pip install telethon playwright browser-cookie3
   playwright install chromium
"""

import asyncio
import json
import logging
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("local_yt_uploader")

# ── Telegram config ───────────────────────────────────────────────────

BOT_USERNAME = "catwood_bot"
ADMIN_ID = 316151942
# Get these from https://my.telegram.org
API_ID = os.environ.get("TG_API_ID")
API_HASH = os.environ.get("TG_API_HASH")
SESSION_FILE = "catwood_admin.session"

# ── paths ─────────────────────────────────────────────────────────────

DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
# Part 1: Telegram Listener (Telethon)
# ═══════════════════════════════════════════════════════════════════════

class TelegramListener:
    """Listen for new video messages from CatWood Bot."""

    def __init__(self, api_id: int, api_hash: str):
        from telethon import TelegramClient
        self.client = TelegramClient(SESSION_FILE, api_id, api_hash)
        self._bot_entity = None

    async def start(self):
        await self.client.start()
        me = await self.client.get_me()
        logger.info(f"Logged in as @{me.username or me.first_name} (id={me.id})")

        # Resolve bot
        self._bot_entity = await self.client.get_entity(BOT_USERNAME)
        logger.info(f"Watching for messages from @{BOT_USERNAME}")

    async def listen(self, on_video):
        """Listen for new messages with video files from the bot."""
        @self.client.on(events_from_bot())
        async def handler(event):
            msg = event.message
            if not msg or not msg.file or not msg.file.mime_type:
                return
            # Only video files
            if not msg.file.mime_type.startswith("video/"):
                return
            caption = (msg.text or msg.file.name or "")
            if "#youtube_upload" not in caption:
                return
            logger.info(f"🎬 New video from bot: {msg.file.name} ({msg.file.size} bytes)")
            await on_video(msg)

        logger.info("Listening... (Ctrl+C to stop)")
        await self.client.run_until_disconnected()

    def events_from_bot(self):
        from telethon import events
        return events.NewMessage(chats=self._bot_entity)


# ═══════════════════════════════════════════════════════════════════════
# Part 2: YouTube Upload (Playwright + browser-cookie3)
# ═══════════════════════════════════════════════════════════════════════

class YouTubeStudioUploader:
    """Upload video to YouTube Studio via Playwright with Chrome cookies."""

    UPLOAD_URL = "https://studio.youtube.com"
    UPLOAD_TIMEOUT = 300_000  # 5 min for upload+processing

    def __init__(self):
        self._cookies = None

    def get_chrome_cookies(self):
        """Extract YouTube cookies from Chrome via browser-cookie3."""
        import browser_cookie3
        try:
            cj = browser_cookie3.chrome(domain_name=".youtube.com")
            cookies = []
            for c in cj:
                cookies.append({
                    "name": c.name,
                    "value": c.value,
                    "domain": c.domain,
                    "path": c.path or "/",
                    "secure": c.secure,
                    "httpOnly": hasattr(c, "http_only") and c.http_only,
                    "sameSite": "Lax",
                })
            # Also get google.com cookies (SAPISID, etc. often on .google.com)
            try:
                cj2 = browser_cookie3.chrome(domain_name=".google.com")
                for c in cj2:
                    if c.name in ("SAPISID", "__Secure-3PAPISID", "__Secure-1PAPISID",
                                  "__Secure-3PSID", "LOGIN_INFO", "HSID", "SSID", "SID"):
                        cookies.append({
                            "name": c.name,
                            "value": c.value,
                            "domain": ".youtube.com",  # force to youtube domain
                            "path": "/",
                            "secure": c.secure,
                            "httpOnly": hasattr(c, "http_only") and c.http_only,
                            "sameSite": "Lax",
                        })
            except Exception:
                pass
            self._cookies = cookies
            logger.info(f"Extracted {len(cookies)} cookies from Chrome")
            return cookies
        except Exception as e:
            logger.error(f"Failed to get Chrome cookies: {e}")
            raise

    def upload(self, video_path: str, title: str, description: str, visibility: str = "unlisted"):
        """Upload video to YouTube Studio via Playwright."""
        from playwright.sync_api import sync_playwright

        if not self._cookies:
            self.get_chrome_cookies()

        visibility = visibility.lower()

        with sync_playwright() as p:
            # Launch Chromium with Chrome's cookie (headless=False for reliability)
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,  # Show browser so user sees progress
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )

            # Inject cookies before navigating
            context.add_cookies(self._cookies)
            page = context.new_page()

            try:
                # Step 1: Navigate to YouTube Studio
                logger.info("Opening YouTube Studio...")
                page.goto(self.UPLOAD_URL, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)  # Let JS render

                # Check if logged in
                if "login" in page.url.lower() or "signin" in page.url.lower():
                    raise RuntimeError(
                        "Redirected to login page. "
                        "Make sure you're logged into YouTube in Chrome."
                    )

                # Step 2: Click Create → Upload video
                logger.info("Clicking Create...")
                create_btn = page.locator("text=Create").first
                create_btn.wait_for(timeout=15000)
                create_btn.click()
                page.wait_for_timeout(1000)

                logger.info("Clicking Upload video...")
                upload_btn = page.locator("text=Upload video").first
                upload_btn.wait_for(timeout=5000)
                upload_btn.click()

                # Step 3: Select file
                logger.info(f"Selecting file: {video_path}")
                file_input = page.locator('input[type="file"]').first
                file_input.set_input_files(video_path)

                # Step 4: Wait for upload details form
                logger.info("Waiting for upload to process...")
                page.wait_for_timeout(5000)

                # Look for title/description fields
                # YouTube Studio uses different selectors, try multiple
                title_input = page.locator("#title-textarea").first
                desc_input = page.locator("#description-textarea").first

                try:
                    title_input.wait_for(timeout=self.UPLOAD_TIMEOUT)
                except Exception:
                    # Try alternative selector
                    title_input = page.locator("[aria-label*='Title']").first
                    title_input.wait_for(timeout=30000)

                # Step 5: Fill title
                title_text = title[:100]
                title_input.click()
                title_input.fill("")
                page.wait_for_timeout(500)
                title_input.fill(title_text)
                logger.info(f"Title set: {title_text}")

                # Step 6: Fill description
                desc_text = description[:5000]
                try:
                    desc_input.wait_for(timeout=5000)
                    desc_input.click()
                    desc_input.fill("")
                    page.wait_for_timeout(500)
                    desc_input.fill(desc_text)
                    logger.info("Description set")
                except Exception:
                    logger.warning("Could not find description field, skipping")

                # Step 7: Set visibility
                logger.info(f"Setting visibility: {visibility}")
                try:
                    # Find visibility radio/section
                    if visibility == "public":
                        page.locator("text=Public").first.click()
                    elif visibility == "unlisted":
                        page.locator("text=Unlisted").first.click()
                    elif visibility == "private":
                        page.locator("text=Private").first.click()
                    page.wait_for_timeout(500)
                except Exception as e:
                    logger.warning(f"Could not set visibility: {e}")

                # Step 8: Click Publish (or Next → Next → Publish)
                logger.info("Publishing...")
                try:
                    publish_btn = page.locator("text=Publish").first
                    publish_btn.wait_for(timeout=10000)
                    publish_btn.click()
                except Exception:
                    # Maybe need to go through Next → Next → Publish
                    for _ in range(3):
                        try:
                            next_btn = page.locator("text=Next").first
                            if next_btn.is_visible():
                                next_btn.click()
                                page.wait_for_timeout(1000)
                        except Exception:
                            break
                    try:
                        publish_btn = page.locator("text=Publish").first
                        publish_btn.click()
                    except Exception:
                        # Might already be published
                        pass

                # Step 9: Wait for confirmation
                page.wait_for_timeout(5000)
                logger.info("✅ Done! Video should be published.")

            except Exception as e:
                logger.error(f"Upload failed: {e}")
                # Take screenshot for debugging
                try:
                    page.screenshot(path="upload_error.png")
                    logger.info("Screenshot saved to upload_error.png")
                except Exception:
                    pass
                raise
            finally:
                page.wait_for_timeout(2000)
                browser.close()


# ═══════════════════════════════════════════════════════════════════════
# Part 3: Main Loop
# ═══════════════════════════════════════════════════════════════════════

def parse_caption(caption: str) -> dict[str, str]:
    """Extract metadata from #youtube_upload caption."""
    title = ""
    description = ""
    visibility = "unlisted"

    for line in caption.split("\n"):
        line = line.strip()
        if line.startswith("TITLE:"):
            title = line[6:].strip()
        elif line.startswith("DESC:"):
            description = line[5:].strip()
        elif line.startswith("VISIBILITY:"):
            visibility = line[11:].strip().lower()

    return {"title": title, "description": description, "visibility": visibility}


async def handle_video(msg):
    """Download video from Telegram and upload to YouTube."""
    # Step 1: Download
    file_name = msg.file.name or f"totem_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    safe_name = re.sub(r'[^\w\-_\. ]', '_', file_name)
    local_path = DOWNLOADS_DIR / safe_name

    logger.info(f"Downloading {file_name}...")
    await msg.download_media(str(local_path))
    logger.info(f"Downloaded to {local_path} ({local_path.stat().st_size} bytes)")

    # Step 2: Parse metadata
    caption = (msg.text or msg.file.name or "")
    meta = parse_caption(caption)
    if not meta["title"]:
        meta["title"] = local_path.stem.replace("_", " ").title()
    logger.info(f"Metadata: {meta}")

    # Step 3: Upload to YouTube
    logger.info("Starting YouTube upload...")
    uploader = YouTubeStudioUploader()
    try:
        uploader.upload(
            video_path=str(local_path),
            title=meta["title"],
            description=meta["description"],
            visibility=meta["visibility"],
        )
        logger.info("✅ YouTube upload complete!")
    except Exception as e:
        logger.error(f"❌ YouTube upload failed: {e}")
    finally:
        # Clean up downloaded file
        local_path.unlink(missing_ok=True)


async def main():
    if not API_ID or not API_HASH:
        print("=" * 60)
        print("  LOCAL YOUTUBE UPLOADER FOR CATWOOD BOT")
        print("=" * 60)
        print()
        print("First time setup:")
        print("1. Go to https://my.telegram.org/apps")
        print("2. Create an app, copy API ID and API Hash")
        print("3. Set environment variables or edit this file:")
        print("   set TG_API_ID=your_id")
        print("   set TG_API_HASH=your_hash")
        print()
        print("   Or run:")
        print(f"   $env:TG_API_ID='your_id'; $env:TG_API_HASH='your_hash'; python local_yt_uploader.py")
        print()
        sys.exit(1)

    listener = TelegramListener(int(API_ID), API_HASH)
    await listener.start()
    await listener.listen(handle_video)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
