"""
Local YouTube Shorts uploader for CatWood Bot.
- Auto-login to Google via YT_EMAIL / YT_PASSWORD
- Saves Playwright storage state to avoid re-login
- Processes all queued videos, then sleeps 2 hours
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("local_uploader")

# ── Config ────────────────────────────────────────────────────────────

YT_BOT_TOKEN    = os.environ.get("YT_BOT_TOKEN", "")
YT_EMAIL        = os.environ.get("YT_EMAIL", "catwoodtotem@gmail.com")
YT_PASSWORD     = os.environ.get("YT_PASSWORD", "UpLogtiq1234")
DOWNLOAD_DIR    = Path(os.environ.get("DOWNLOAD_DIR", "downloads"))
VISIBILITY      = os.environ.get("YT_VISIBILITY", "public")
STATE_FILE      = Path("youtube_state.json")
CLEANUP_AFTER   = True

DOWNLOAD_DIR.mkdir(exist_ok=True)

# ── Caption parser ───────────────────────────────────────────────────

def parse_yt_caption(caption: str) -> dict:
    meta = {"title": "", "description": "", "visibility": VISIBILITY, "user_id": ""}
    for line in caption.split("\n"):
        line = line.strip()
        if line.startswith("TITLE:"):
            meta["title"] = line[6:].strip()
        elif line.startswith("DESC:"):
            meta["description"] = line[5:].strip()
        elif line.startswith("VISIBILITY:"):
            parts = line[11:].strip().split("|")
            meta["visibility"] = parts[0].strip().lower()
            if len(parts) > 1 and parts[1].strip().startswith("USER:"):
                meta["user_id"] = parts[1].strip()[5:].strip()
    return meta


# ═══════════════════════════════════════════════════════════════════════
# YouTube Upload via Playwright (auto-login + storage state)
# ═══════════════════════════════════════════════════════════════════════

def ensure_logged_in(context, page) -> bool:
    """Check if already logged in. If not, auto-login with credentials."""
    page.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    if "accounts.google.com" not in page.url and "ServiceLogin" not in page.url:
        logger.info("✅ Already logged in (session valid)")
        return True

    if not YT_EMAIL or not YT_PASSWORD:
        logger.warning("🔐 YT_EMAIL / YT_PASSWORD not set — waiting 120s for manual login...")
        try:
            page.wait_for_url("https://studio.youtube.com/**", timeout=120_000)
            logger.info("✅ Manual login successful")
            return True
        except Exception:
            raise RuntimeError("Manual login timeout. Set YT_EMAIL + YT_PASSWORD and retry.")

    logger.info("🔐 Auto-login with credentials...")
    try:
        # Email
        email_input = page.locator("#identifierId").first
        email_input.wait_for(timeout=10000)
        email_input.click()
        email_input.fill(YT_EMAIL)
        page.wait_for_timeout(500)
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)

        # Password
        pwd_input = page.locator("#password input, [name='Passwd'], #password").first
        pwd_input.wait_for(timeout=15000)
        pwd_input.click()
        pwd_input.fill(YT_PASSWORD)
        page.wait_for_timeout(500)
        page.keyboard.press("Enter")

        # Wait for redirect to studio
        page.wait_for_url("https://studio.youtube.com/**", timeout=30000)
        logger.info("✅ Auto-login successful!")

        # Save storage state for future runs
        state_path = str(STATE_FILE.resolve())
        context.storage_state(path=state_path)
        logger.info(f"💾 Saved session state to {state_path}")
        return True
    except Exception as e:
        raise RuntimeError(f"Auto-login failed: {e}. Check YT_EMAIL / YT_PASSWORD.")


def upload_video(context, page, video_path: str, title: str, description: str, visibility: str):
    """Upload a single video to YouTube using an already-logged-in session."""
    visibility = visibility.lower()
    if visibility not in ("public", "unlisted", "private"):
        visibility = "unlisted"

    logger.info(f"📤 Uploading: {title}")

    # Navigate directly to upload page
    page.goto("https://www.youtube.com/upload", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    # File picker
    logger.info(f"📁 Selecting file: {Path(video_path).name}")
    try:
        page.wait_for_timeout(1000)
        with page.expect_file_chooser(timeout=15000) as fc_info:
            selectors = [
                "text=SELECT FILES", "text=Select Files", "text=Выбрать файл",
                "ytcp-button#select-files-button", "[data-testid='file-input']",
                "#select-files-button", "input[type='file']",
            ]
            clicked = False
            for sel in selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=1000):
                        btn.click()
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                page.keyboard.press("Enter")
                page.wait_for_timeout(1000)
                page.keyboard.press("Enter")
        file_chooser = fc_info.value
        file_chooser.set_files(video_path)
        logger.info("✅ File selected")
    except Exception as e:
        raise RuntimeError(f"Could not select file: {e}")

    # Wait for upload processing
    logger.info("⏳ Waiting for upload...")
    title_input = page.locator("#title-textarea, [aria-label*='Title']").first
    title_input.wait_for(timeout=600_000)

    # Fill title
    logger.info(f"📝 Title: {title}")
    title_input.click()
    page.wait_for_timeout(500)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    page.keyboard.type(title[:100], delay=30)
    page.wait_for_timeout(500)

    # Fill description
    logger.info("📝 Description...")
    try:
        desc_input = page.locator("#description-textarea, [aria-label*='Description']").first
        desc_input.wait_for(timeout=5000)
        desc_input.click()
        page.wait_for_timeout(300)
        page.keyboard.press("Control+a")
        page.keyboard.press("Delete")
        page.keyboard.type(description[:5000], delay=15)
        page.wait_for_timeout(300)
    except Exception as e:
        logger.warning(f"Skipping description: {e}")

    # Visibility
    logger.info(f"🔒 Visibility: {visibility}")
    try:
        page.mouse.wheel(0, 600)
        page.wait_for_timeout(500)
        vis_btn = page.locator(f"text={visibility.capitalize()}").first
        if vis_btn.is_visible(timeout=2000):
            vis_btn.click()
            page.wait_for_timeout(500)
    except Exception:
        pass

    # Publish
    logger.info("🚀 Publishing...")
    try:
        publish_btn = page.locator("text=Publish").first
        publish_btn.wait_for(timeout=10000)
        publish_btn.click()
        logger.info("✅ Published!")
    except Exception:
        try:
            page.locator("text=Done").first.click()
            page.wait_for_timeout(1000)
            page.locator("text=Publish").first.click()
            logger.info("✅ Published!")
        except Exception:
            logger.warning("Could not click Publish, might be already processing")

    page.wait_for_timeout(5000)
    try:
        page.wait_for_selector(
            "text=Upload complete, text=Published, text=Video processed",
            timeout=60000,
        )
    except Exception:
        pass
    logger.info("✅ YouTube upload complete!")


# ═══════════════════════════════════════════════════════════════════════
# Telegram Polling (one-shot: fetch all pending, process, return)
# ═══════════════════════════════════════════════════════════════════════

def fetch_pending_videos() -> list[dict]:
    """Fetch all pending #youtube_upload videos from the channel."""
    import requests as req

    videos = []
    last_update_id = 0

    url = f"https://api.telegram.org/bot{YT_BOT_TOKEN}/getUpdates"
    params = {
        "offset": -1,
        "timeout": 5,
        "allowed_updates": json.dumps(["channel_post"]),
    }
    try:
        r = req.get(url, params=params, timeout=10)
        data = r.json()
        if not data.get("ok"):
            logger.warning(f"API error: {data}")
            return videos
        for update in data.get("result", []):
            update_id = update["update_id"]
            last_update_id = max(last_update_id, update_id)
            msg = update.get("channel_post") or update.get("message")
            if not msg:
                continue
            caption = msg.get("caption", "") or ""
            if "#youtube_upload" not in caption:
                continue
            video = msg.get("video") or msg.get("video_note")
            if not video:
                doc = msg.get("document")
                if doc and doc.get("mime_type", "").startswith("video/"):
                    video = doc
            if not video:
                continue
            videos.append({
                "file_id": video["file_id"],
                "caption": caption,
                "update_id": update_id,
            })
        # Mark them as read
        if last_update_id > 0:
            req.get(url, params={"offset": last_update_id + 1, "timeout": 1}, timeout=5)
    except Exception as e:
        logger.error(f"Poll error: {e}")

    return videos


def download_video(video_info: dict) -> tuple[Path, dict]:
    """Download a video from Telegram, return (local_path, meta)."""
    import requests as req

    file_id = video_info["file_id"]
    caption = video_info["caption"]
    meta = parse_yt_caption(caption)

    fr = req.get(
        f"https://api.telegram.org/bot{YT_BOT_TOKEN}/getFile?file_id={file_id}",
        timeout=10,
    )
    fd = fr.json()
    if not fd.get("ok"):
        raise RuntimeError(f"getFile failed: {fd}")

    file_path = fd["result"]["file_path"]
    download_url = f"https://api.telegram.org/file/bot{YT_BOT_TOKEN}/{file_path}"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_path = DOWNLOAD_DIR / f"totem_{timestamp}.mp4"
    logger.info("Downloading from Telegram...")
    dr = req.get(download_url, timeout=300)
    local_path.write_bytes(dr.content)
    logger.info(f"Downloaded: {local_path} ({local_path.stat().st_size} bytes)")

    return local_path, meta


# ═══════════════════════════════════════════════════════════════════════
# Main loop: process queue, then sleep 2 hours
# ═══════════════════════════════════════════════════════════════════════

RUN_SCHEDULE = 2 * 60 * 60  # 2 hours in seconds


def process_queue(context, page):
    """Fetch and upload all pending videos."""
    videos = fetch_pending_videos()
    if not videos:
        logger.info("📭 No new videos in queue")
        return False

    logger.info(f"📦 Found {len(videos)} video(s) in queue")
    for v in videos:
        try:
            local_path, meta = download_video(v)
            title = meta["title"] or local_path.stem
            desc = meta["description"] or ""
            vis = meta["visibility"] or VISIBILITY
            if "#Shorts" not in desc and "#shorts" not in desc:
                desc += "\n\n#Shorts"

            upload_video(context, page, str(local_path), title, desc, vis)

            # Mark update as processed via offset
            update_id = v.get("update_id", 0)
            if update_id:
                import requests as req
                req.get(
                    f"https://api.telegram.org/bot{YT_BOT_TOKEN}/getUpdates",
                    params={"offset": update_id + 1, "timeout": 1},
                    timeout=5,
                )
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
        finally:
            if CLEANUP_AFTER and local_path:
                local_path.unlink(missing_ok=True)
                logger.info(f"Cleaned up: {local_path.name}")

    return True


def main_loop():
    """Run forever: process queue → sleep 2h → repeat."""
    from playwright.sync_api import sync_playwright

    logger.info("🐱 CatWood YouTube Uploader — auto-login + 2h loop")
    logger.info(f"📁 Download dir: {DOWNLOAD_DIR.resolve()}")
    logger.info(f"👤 Account: {YT_EMAIL}")
    logger.info(f"🔒 Visibility: {VISIBILITY}")
    logger.info(f"💾 Session state: {STATE_FILE.resolve() if STATE_FILE.exists() else 'not yet saved'}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )

        # Try loading saved state
        if STATE_FILE.exists():
            logger.info("📂 Loading saved session state...")
            context = browser.new_context(
                storage_state=str(STATE_FILE.resolve()),
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
        else:
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )

        page = context.new_page()

        # Ensure logged in (auto-login or session restore)
        try:
            ensure_logged_in(context, page)
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            browser.close()
            return

        # Main loop
        while True:
            try:
                processed = process_queue(context, page)
                if processed:
                    logger.info("✅ Queue processed. Sleeping 2 hours...")
                else:
                    logger.info(f"💤 No videos. Sleeping 2 hours...")
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Loop error: {e}")
                logger.info("💤 Sleeping 2 hours before retry...")

            time.sleep(RUN_SCHEDULE)


# ── Entry ────────────────────────────────────────────────────────────

def main():
    if not YT_BOT_TOKEN:
        print("=" * 60)
        print("  LOCAL YOUTUBE UPLOADER FOR CATWOOD BOT")
        print("=" * 60)
        print()
        print("SETUP:")
        print("1. Create a second bot via @BotFather")
        print("2. Create a private channel, add both bots as admins")
        print("3. Set UPLOAD_CHANNEL_ID in CatWood bot's env vars")
        print("4. Set env vars and run:")
        print()
        print("   $env:YT_BOT_TOKEN='your_token'; python local_uploader.py")
        print()
        return
    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
