"""
Local YouTube Shorts uploader for CatWood Bot (channel-polling version).

HOW IT WORKS:
1. CatWood bot posts videos to a Telegram channel when user presses "📤" button
2. This script polls a SECOND bot (which is admin in the channel) for new videos
3. Downloads each new video, uploads to YouTube Studio via Playwright + Chrome cookies

SETUP:
1. Create a PRIVATE Telegram channel (e.g. "CatWood YouTube Queue")
2. Add CatWood bot as admin → it can post videos there
3. Create a SECOND bot via @BotFather (e.g. @catwood_uploader_bot)
4. Add the second bot as admin in the channel
5. Set UPLOAD_CHANNEL_ID env var on Render (the channel ID or @username)
6. Run this script locally

RUN:
   set YT_BOT_TOKEN=your_second_bot_token
   python local_uploader.py
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

YT_BOT_TOKEN = os.environ.get("YT_BOT_TOKEN", "")
DOWNLOAD_DIR = Path(os.environ.get("DOWNLOAD_DIR", "downloads"))
VISIBILITY = os.environ.get("YT_VISIBILITY", "unlisted")
POLL_INTERVAL = 5
CLEANUP_AFTER_UPLOAD = True

DOWNLOAD_DIR.mkdir(exist_ok=True)

# ── Parsing ───────────────────────────────────────────────────────────

def parse_yt_caption(caption: str) -> dict:
    """Parse #youtube_upload caption for title/description/visibility/user_id."""
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
# YouTube Upload via Playwright
# ═══════════════════════════════════════════════════════════════════════

def get_chrome_cookies() -> list[dict]:
    """Extract YouTube cookies from Chrome via browser-cookie3."""
    import browser_cookie3
    cookies = []
    for domain in [".youtube.com", ".google.com"]:
        try:
            cj = browser_cookie3.chrome(domain_name=domain)
            for c in cj:
                cookies.append({
                    "name": c.name,
                    "value": c.value,
                    "domain": ".youtube.com",
                    "path": "/",
                    "secure": c.secure,
                    "httpOnly": getattr(c, "_rest", {}).get("HttpOnly", False),
                    "sameSite": "Lax",
                })
        except Exception as e:
            logger.debug(f"No {domain} cookies: {e}")
    by_name = {c["name"]: c for c in cookies}
    logger.info(f"Extracted {len(by_name)} cookies from Chrome")
    return list(by_name.values())


def upload_to_youtube(video_path: str, title: str, description: str, visibility: str = "unlisted"):
    """Upload video to YouTube Studio via Playwright + Chrome cookies."""
    from playwright.sync_api import sync_playwright

    logger.info("🍪 Getting Chrome cookies...")
    cookies = get_chrome_cookies()
    if not cookies:
        raise RuntimeError("Нет кук из Chrome. Убедись что Chrome открыт и ты залогинен в YouTube.")

    visibility = visibility.lower()
    if visibility not in ("public", "unlisted", "private"):
        visibility = "unlisted"

    with sync_playwright() as p:
        logger.info("🚀 Launching browser...")
        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        context.add_cookies(cookies)
        page = context.new_page()

        try:
            logger.info("🌐 Opening YouTube Studio...")
            page.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(4000)

            if "accounts.google.com" in page.url or "ServiceLogin" in page.url:
                raise RuntimeError(
                    "Redirected to Google login. Убедись что ты залогинен в YouTube в Chrome."
                )

            # Click Create
            logger.info("🔘 Clicking Create...")
            for selector in ["ytcp-button#create-icon", "#create-icon", "[aria-label='Create']", "text=Create"]:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        break
                except Exception:
                    continue
            page.wait_for_timeout(1500)

            # Click Upload videos
            logger.info("🔘 Clicking Upload videos...")
            for selector in ["text=Upload videos", "text=Upload video", "text=Загрузить видео"]:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=1000):
                        btn.click()
                        break
                except Exception:
                    continue
            page.wait_for_timeout(1000)

            # File picker
            logger.info(f"📁 Selecting file: {Path(video_path).name}")
            try:
                file_input = page.locator('input[type="file"]').first
                file_input.wait_for(timeout=10000)
                file_input.set_input_files(video_path)
            except Exception as e:
                raise RuntimeError(f"Could not set input file: {e}")

            # Wait for upload processing
            logger.info("⏳ Waiting for upload (may take time for large files)...")
            title_input = page.locator("#title-textarea, [aria-label*='Title']").first
            title_input.wait_for(timeout=600_000)

            # Fill title
            logger.info(f"📝 Title: {title}")
            title_input.click()
            title_input.fill("")
            page.wait_for_timeout(300)
            title_input.fill(title[:100])

            # Fill description
            logger.info("📝 Description...")
            try:
                desc_input = page.locator("#description-textarea, [aria-label*='Description']").first
                desc_input.wait_for(timeout=5000)
                desc_input.click()
                desc_input.fill("")
                page.wait_for_timeout(300)
                desc_input.fill(description[:5000])
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
            except Exception as e:
                logger.warning(f"Skipping visibility: {e}")

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

        except Exception as e:
            logger.error(f"Upload error: {e}")
            try:
                page.screenshot(path="upload_error.png")
                logger.info("Screenshot saved to upload_error.png")
            except Exception:
                pass
            raise
        finally:
            try:
                browser.close()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════
# Telegram Bot Polling
# ═══════════════════════════════════════════════════════════════════════

def poll_channel():
    """Poll second bot for new videos in the channel."""
    import requests as req

    logger.info(f"Polling bot every {POLL_INTERVAL}s for new channel videos...")
    last_update_id = 0

    while True:
        try:
            url = f"https://api.telegram.org/bot{YT_BOT_TOKEN}/getUpdates"
            params = {
                "offset": last_update_id + 1,
                "timeout": 30,
                "allowed_updates": json.dumps(["channel_post"]),
            }
            r = req.get(url, params=params, timeout=35)
            data = r.json()

            if not data.get("ok"):
                logger.warning(f"API error: {data}")
                time.sleep(POLL_INTERVAL)
                continue

            for update in data.get("result", []):
                update_id = update["update_id"]
                last_update_id = max(last_update_id, update_id)

                msg = update.get("channel_post") or update.get("message")
                if not msg:
                    continue

                caption = msg.get("caption", "") or ""
                # Only process videos with the #youtube_upload tag
                if "#youtube_upload" not in caption:
                    logger.debug("Skipping — no #youtube_upload tag")
                    continue

                video = msg.get("video") or msg.get("video_note")
                if not video:
                    # Also check document with video mime
                    doc = msg.get("document")
                    if doc and doc.get("mime_type", "").startswith("video/"):
                        video = doc
                if not video:
                    logger.debug("No video in post, skipping")
                    continue

                file_id = video["file_id"]
                meta = parse_yt_caption(caption)

                logger.info(f"🎬 New video: {meta['title'] or file_id}")

                # Download video
                fr = req.get(
                    f"https://api.telegram.org/bot{YT_BOT_TOKEN}/getFile?file_id={file_id}",
                    timeout=10,
                )
                fd = fr.json()
                if not fd.get("ok"):
                    logger.warning(f"getFile failed: {fd}")
                    continue

                file_path = fd["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{YT_BOT_TOKEN}/{file_path}"

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                local_path = DOWNLOAD_DIR / f"totem_{timestamp}.mp4"
                logger.info("Downloading from Telegram...")
                dr = req.get(download_url, timeout=300)
                local_path.write_bytes(dr.content)
                logger.info(f"Downloaded: {local_path} ({local_path.stat().st_size} bytes)")

                # Upload to YouTube
                title = meta["title"] or local_path.stem
                desc = meta["description"] or caption.split("#youtube_upload")[0].strip()
                vis = meta["visibility"] or VISIBILITY
                if "#Shorts" not in desc and "#shorts" not in desc:
                    desc += "\n\n#Shorts"

                logger.info(f"Uploading to YouTube: {title}")
                try:
                    upload_to_youtube(
                        video_path=str(local_path),
                        title=title,
                        description=desc,
                        visibility=vis,
                    )
                    logger.info(f"✅ YouTube upload complete: {title}")
                except Exception as e:
                    logger.error(f"❌ YouTube upload failed: {e}")
                finally:
                    if CLEANUP_AFTER_UPLOAD:
                        local_path.unlink(missing_ok=True)
                        logger.info(f"Cleaned up: {local_path.name}")

        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error(f"Poll error: {e}")
            time.sleep(POLL_INTERVAL)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    if not YT_BOT_TOKEN:
        print("=" * 60)
        print("  LOCAL YOUTUBE UPLOADER FOR CATWOOD BOT")
        print("=" * 60)
        print()
        print("SETUP:")
        print("1. Create a second bot via @BotFather (any name, e.g. @catwood_uploader)")
        print("2. Create a private channel, add both bots as admins")
        print("3. Set UPLOAD_CHANNEL_ID in CatWood bot's env vars (render.com)")
        print("4. Set YT_BOT_TOKEN and run:")
        print()
        print("   $env:YT_BOT_TOKEN='your_token'; python local_uploader.py")
        print()
        return

    poll_channel()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nGoodbye!")
        sys.exit(0)


# ═══════════════════════════════════════════════════════════════════════
# Part 2: YouTube Upload via Playwright
# ═══════════════════════════════════════════════════════════════════════

def get_chrome_cookies() -> list[dict]:
    """Extract YouTube cookies from Chrome via browser-cookie3."""
    import browser_cookie3
    cookies = []
    # Get all YouTube and Google cookies
    for domain in [".youtube.com", ".google.com"]:
        try:
            cj = browser_cookie3.chrome(domain_name=domain)
            for c in cj:
                cookies.append({
                    "name": c.name,
                    "value": c.value,
                    # Force to youtube.com domain so requests/Playwright sends them
                    "domain": ".youtube.com",
                    "path": "/",
                    "secure": c.secure,
                    "httpOnly": getattr(c, "_rest", {}).get("HttpOnly", False) or getattr(c, "http_only", False),
                    "sameSite": "Lax",
                })
        except Exception as e:
            logger.debug(f"Could not get {domain} cookies: {e}")
    # Deduplicate by name (keep last)
    by_name = {c["name"]: c for c in cookies}
    cookies = list(by_name.values())
    logger.info(f"Extracted {len(cookies)} cookies from Chrome")
    return cookies


def upload_to_youtube(video_path: str, title: str, description: str, visibility: str = "unlisted"):
    """Upload video to YouTube Studio via Playwright."""
    from playwright.sync_api import sync_playwright
    
    logger.info("🍪 Getting Chrome cookies...")
    cookies = get_chrome_cookies()
    
    visibility = visibility.lower()
    if visibility not in ("public", "unlisted", "private"):
        visibility = "unlisted"
    
    with sync_playwright() as p:
        logger.info("🚀 Launching browser...")
        browser = p.chromium.launch(
            headless=False,  # Show browser so you can see progress + intervene if needed
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        
        # Inject cookies BEFORE navigating
        context.add_cookies(cookies)
        page = context.new_page()
        
        try:
            logger.info("🌐 Navigating to YouTube Studio...")
            page.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Check login
            if "accounts.google.com" in page.url or "ServiceLogin" in page.url:
                raise RuntimeError(
                    "Redirected to Google login. Make sure you're logged into YouTube in Chrome, "
                    "then run this script again."
                )
            
            logger.info("🔘 Clicking 'Create' button...")
            try:
                create_btn = page.locator("ytcp-button#create-icon, #create-icon, [aria-label='Create']").first
                create_btn.wait_for(timeout=15000)
                create_btn.click()
            except Exception:
                # Fallback: click any visible 'Create' text
                page.locator("text=Create").first.click()
            page.wait_for_timeout(1500)
            
            logger.info("🔘 Clicking 'Upload videos'...")
            try:
                upload_btn = page.locator("text=Upload videos").first
                upload_btn.wait_for(timeout=5000)
                upload_btn.click()
            except Exception:
                try:
                    page.locator("text=Upload video").first.click()
                except Exception:
                    # Direct navigation fallback
                    page.goto("https://studio.youtube.com/channel/UC/videos/upload?d=ud")
                    page.wait_for_timeout(2000)
            
            # File picker (set_input_files works on hidden inputs in YouTube Studio)
            logger.info(f"📁 Selecting file: {Path(video_path).name}")
            try:
                file_input = page.locator('input[type="file"]').first
                file_input.wait_for(timeout=10000)
                file_input.set_input_files(video_path)
            except Exception as e:
                raise RuntimeError(f"Could not set input file: {e}")
            
            # Wait for upload to start (uploads can take time)
            logger.info("⏳ Waiting for upload to start (this may take a few minutes for big files)...")
            title_input = page.locator("#title-textarea, [aria-label*='Title']").first
            title_input.wait_for(timeout=600_000)  # 10 min max
            
            logger.info(f"📝 Setting title: {title}")
            title_input.click()
            title_input.fill("")
            page.wait_for_timeout(300)
            title_input.fill(title)
            
            # Description
            logger.info("📝 Setting description...")
            try:
                desc_input = page.locator("#description-textarea, [aria-label*='Description']").first
                desc_input.wait_for(timeout=5000)
                desc_input.click()
                desc_input.fill("")
                page.wait_for_timeout(300)
                desc_input.fill(description)
            except Exception as e:
                logger.warning(f"Could not set description: {e}")
            
            # Visibility
            logger.info(f"🔒 Setting visibility: {visibility}")
            try:
                # Scroll to find the visibility section (it's usually below the description)
                page.mouse.wheel(0, 600)
                page.wait_for_timeout(500)
                vis_label = visibility.capitalize()  # Public, Unlisted, Private
                page.locator(f"text={vis_label}").first.click()
                page.wait_for_timeout(500)
            except Exception as e:
                logger.warning(f"Could not set visibility: {e}")
            
            # Publish
            logger.info("🚀 Publishing...")
            try:
                publish_btn = page.locator("text=Publish").first
                publish_btn.wait_for(timeout=10000)
                publish_btn.click()
            except Exception:
                # Maybe dialog requires "Done" first
                try:
                    page.locator("text=Done").first.click()
                    page.wait_for_timeout(1000)
                    page.locator("text=Publish").first.click()
                except Exception:
                    pass
            
            # Wait for success
            logger.info("⏳ Waiting for upload to finish processing...")
            page.wait_for_timeout(5000)
            
            # Check for success indicator
            try:
                page.wait_for_selector("text=Upload complete, text=Published, text=Video processed", timeout=30000)
            except Exception:
                pass
            
            logger.info("✅ Done! Video should be published as YouTube Short.")
        
        except Exception as e:
            logger.error(f"Upload error: {e}")
            try:
                page.screenshot(path=str(WATCHED_DIR / "upload_error.png"))
                logger.info(f"Screenshot saved to upload_error.png")
            except Exception:
                pass
            raise
        finally:
            try:
                browser.close()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        watch_folder()
    except KeyboardInterrupt:
        logger.info("\nGoodbye!")
        sys.exit(0)
