"""
Local YouTube Shorts uploader for CatWood Bot (folder-watcher version).

ZERO-CONFIG: just install deps, run script, and save videos to the watched folder.

HOW IT WORKS:
1. Save totem video (from CatWood bot in Telegram) to the watched folder
2. Optionally save a sidecar .txt with description (or skip — auto-generates)
3. Script auto-detects new file, uploads to YouTube with all metadata
4. Moves uploaded file to uploaded/ subfolder

SETUP (one-time):
    pip install playwright watchdog
    playwright install chromium

RUN:
    python local_uploader.py
    
The default watched folder is: %USERPROFILE%/Videos/yt_upload
Change WATCHED_DIR at the top of this file if you want a different folder.
"""

import os
import re
import sys
import time
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("local_uploader")

# ── Configuration ─────────────────────────────────────────────────────

# Folder to watch for new MP4 files
WATCHED_DIR = Path(os.environ.get("WATCHED_DIR", Path.home() / "Videos" / "yt_upload"))

# Where to move files after upload
UPLOADED_DIR = WATCHED_DIR / "uploaded"

# Visibility for all uploads (unlisted/private/public)
VISIBILITY = "unlisted"

# Optional: add a footer to every description
DESCRIPTION_FOOTER = "\n\n#Shorts #CatWood #Totem #Meow"

# Default title template (used if no sidecar .txt found)
# %s will be replaced with the filename (without extension)
DEFAULT_TITLE_TEMPLATE = "%s 🐱"

# ── Files ─────────────────────────────────────────────────────────────

WATCHED_DIR.mkdir(parents=True, exist_ok=True)
UPLOADED_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
# Part 1: File Watcher
# ═══════════════════════════════════════════════════════════════════════

def get_metadata(video_path: Path) -> dict:
    """Extract metadata from sidecar .txt or auto-generate from filename."""
    sidecar = video_path.with_suffix(".txt")
    title = DEFAULT_TITLE_TEMPLATE % video_path.stem.replace("_", " ")
    description = ""
    
    if sidecar.is_file():
        logger.info(f"Found sidecar: {sidecar.name}")
        try:
            text = sidecar.read_text(encoding="utf-8").strip()
            # First line = title, rest = description
            lines = text.split("\n", 1)
            if lines and lines[0].strip():
                title = lines[0].strip()
            if len(lines) > 1 and lines[1].strip():
                description = lines[1].strip()
        except Exception as e:
            logger.warning(f"Failed to read sidecar: {e}")
    
    return {
        "title": title[:100],
        "description": (description + DESCRIPTION_FOOTER)[:5000],
        "visibility": VISIBILITY,
    }


def wait_for_file_stable(path: Path, min_wait: float = 2.0, stable_for: float = 2.0) -> bool:
    """Wait until file size stops changing (i.e., download/copy finished)."""
    logger.info(f"Waiting for file to finish writing: {path.name}")
    start = time.time()
    last_size = -1
    stable_since = None
    while time.time() - start < 60:  # max 1 min
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False
        if size == last_size and size > 0:
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since >= stable_for:
                return True
        else:
            stable_since = None
            last_size = size
        time.sleep(0.5)
    return True  # timeout but proceed


def scan_existing_files() -> set[Path]:
    """Return set of files that exist at startup (to ignore them)."""
    if not WATCHED_DIR.is_dir():
        return set()
    return set(p for p in WATCHED_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".mp4")


def watch_folder():
    """Watch folder for new .mp4 files."""
    logger.info(f"Watching folder: {WATCHED_DIR}")
    logger.info(f"Will move uploaded files to: {UPLOADED_DIR}")
    logger.info(f"Press Ctrl+C to stop.\n")
    
    known = scan_existing_files()
    if known:
        logger.info(f"Ignoring {len(known)} existing files.")
    
    while True:
        try:
            current = set(p for p in WATCHED_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".mp4")
            new_files = current - known
            for path in new_files:
                if not path.is_file():
                    continue
                if not wait_for_file_stable(path):
                    logger.warning(f"File disappeared: {path}")
                    continue
                logger.info(f"\n{'='*60}")
                logger.info(f"📥 New file: {path.name} ({path.stat().st_size} bytes)")
                logger.info(f"{'='*60}")
                try:
                    handle_new_file(path)
                except Exception as e:
                    logger.error(f"Failed to handle {path.name}: {e}")
            known = current
        except KeyboardInterrupt:
            logger.info("\nStopped by user")
            break
        except Exception as e:
            logger.error(f"Watcher error: {e}")
        time.sleep(2)


def handle_new_file(video_path: Path):
    """Process one new video: upload to YouTube, move to uploaded/."""
    meta = get_metadata(video_path)
    logger.info(f"Title: {meta['title']}")
    logger.info(f"Description: {meta['description'][:200]}{'...' if len(meta['description']) > 200 else ''}")
    logger.info(f"Visibility: {meta['visibility']}")
    
    # Upload
    try:
        upload_to_youtube(
            video_path=str(video_path),
            title=meta["title"],
            description=meta["description"],
            visibility=meta["visibility"],
        )
        # Move to uploaded/
        dest = UPLOADED_DIR / video_path.name
        if dest.exists():
            dest = UPLOADED_DIR / f"{video_path.stem}_{int(time.time())}{video_path.suffix}"
        shutil.move(str(video_path), str(dest))
        # Move sidecar too if exists
        sidecar = video_path.with_suffix(".txt")
        if sidecar.is_file():
            shutil.move(str(sidecar), str(dest.with_suffix(".txt")))
        logger.info(f"✅ Moved to {dest.name}")
    except Exception as e:
        logger.error(f"❌ Upload failed for {video_path.name}: {e}")
        # Move to failed/ for retry
        failed_dir = WATCHED_DIR / "failed"
        failed_dir.mkdir(exist_ok=True)
        try:
            dest = failed_dir / video_path.name
            if dest.exists():
                dest = failed_dir / f"{video_path.stem}_{int(time.time())}{video_path.suffix}"
            shutil.move(str(video_path), str(dest))
            logger.info(f"Moved to {dest}")
        except Exception:
            pass


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
