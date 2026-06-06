"""
YouTube Shorts uploader via YouTube Internal API (HTTP requests, no browser).
Uses existing login cookies from DB.

Requires: aiohttp (already in requirements.txt)

Usage:
    from youtube_api import upload_short
    ok = await upload_short("video.mp4", "Title", "Description", cookies_list)
"""

import asyncio
import json
import logging
import re
import uuid
from pathlib import Path

import aiohttp

logger = logging.getLogger("youtube_api")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Default API key (also extracted from page as fallback)
DEFAULT_API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"

TIMEOUT = aiohttp.ClientTimeout(total=300)


# ── helpers ──────────────────────────────────────────────────────────

def _cookie_dict(cookies: list[dict]) -> dict[str, str]:
    """Convert cookies list to a simple dict for aiohttp ClientSession."""
    return {c["name"]: c["value"] for c in cookies if "name" in c and "value" in c}


def _make_context(client_version: str | None = None) -> dict:
    """Return the standard YouTubei API context block."""
    return {
        "client": {
            "clientName": "WEB",
            "clientVersion": client_version or "2.20250101.00.00",
        },
    }


async def _fetch_tokens(session: aiohttp.ClientSession) -> tuple:
    """Extract API key, identity token, and client version from youtube.com/upload."""
    async with session.get(
        "https://www.youtube.com/upload",
        allow_redirects=True,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as resp:
        html = await resp.text()

    api_key = DEFAULT_API_KEY
    id_token = None
    client_version = None

    m = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html)
    if m:
        api_key = m.group(1)
        logger.debug(f"Extracted API key from page")

    m = re.search(r'"ID_TOKEN":"([^"]+)"', html)
    if m:
        id_token = m.group(1)
        logger.debug(f"Extracted ID token")

    m = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', html)
    if m:
        client_version = m.group(1)
        logger.debug(f"Extracted client version: {client_version}")

    return api_key, id_token, client_version


async def _create_upload_session(
    session: aiohttp.ClientSession,
    api_key: str,
    id_token: str,
    client_version: str,
    file_size: int,
    file_name: str,
) -> dict | None:
    """Create a Scotty upload session via YouTubei API.
    Returns the response dict on success, None on failure."""
    frontend_id = f"uuid-{uuid.uuid4()}"

    payload = {
        "context": _make_context(client_version),
        "frontendUploadId": frontend_id,
        "resource": {
            "fileName": file_name,
            "fileSize": str(file_size),
        },
    }

    headers = {
        "X-YouTube-Identity-Token": id_token,
        "Content-Type": "application/json",
        "Origin": "https://www.youtube.com",
        "X-YouTube-Client-Name": "1",
        "X-YouTube-Client-Version": client_version,
    }

    async with session.post(
        f"https://www.youtube.com/youtubei/v1/upload/createsession?key={api_key}",
        json=payload,
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as resp:
        if resp.status != 200:
            text = await resp.text()
            logger.error(f"Create session failed (HTTP {resp.status}): {text[:300]}")
            return None
        result = await resp.json()
        logger.debug(f"Create session OK")
        return result


async def _upload_binary(
    upload_url: str,
    mp4_path: Path,
) -> bool:
    """Upload video binary to Scotty via PUT.
    Uses a separate session to avoid cookie interference."""
    file_size = mp4_path.stat().st_size
    headers = {
        "Content-Type": "video/mp4",
        "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
    }

    try:
        async with aiohttp.ClientSession() as us:
            # Use read() + data to stream from file
            with open(mp4_path, "rb") as f:
                data = f.read()
            async with us.put(
                upload_url,
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=600),
            ) as resp:
                if resp.status in (200, 201, 204):
                    logger.info(f"Binary upload OK ({resp.status})")
                    return True
                else:
                    text = await resp.text()
                    logger.error(f"Binary upload failed (HTTP {resp.status}): {text[:300]}")
                    return False
    except Exception as e:
        logger.error(f"Binary upload exception: {e}")
        return False


async def _process_pending(
    session: aiohttp.ClientSession,
    api_key: str,
    id_token: str,
    client_version: str,
    video_id: str,
    title: str,
    description: str,
    visibility: str,
) -> bool:
    """Set video metadata and trigger processing via YouTubei API."""
    visibility_map = {
        "public": "PUBLIC",
        "private": "PRIVATE",
        "unlisted": "UNLISTED",
    }
    privacy = visibility_map.get(visibility.lower(), "UNLISTED")

    payload = {
        "context": _make_context(client_version),
        "encryptedVideoId": video_id,
        "title": title,
        "description": description,
        "privacy": privacy,
        "categoryId": "22",  # People & Blogs
    }

    headers = {
        "X-YouTube-Identity-Token": id_token,
        "Content-Type": "application/json",
        "Origin": "https://www.youtube.com",
        "X-YouTube-Client-Name": "1",
        "X-YouTube-Client-Version": client_version,
    }

    async with session.post(
        f"https://www.youtube.com/youtubei/v1/upload/processpending?key={api_key}",
        json=payload,
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=60),
    ) as resp:
        if resp.status != 200:
            text = await resp.text()
            logger.error(f"Process pending failed (HTTP {resp.status}): {text[:300]}")
            return False
        result = await resp.json()
        logger.info(f"Process pending OK — video {video_id} set to {privacy}")
        return True


async def _set_thumbnail(
    session: aiohttp.ClientSession,
    api_key: str,
    id_token: str,
    client_version: str,
    video_id: str,
) -> bool:
    """Try to auto-generate a thumbnail. Non-critical, best-effort."""
    try:
        payload = {
            "context": _make_context(client_version),
            "encryptedVideoId": video_id,
        }
        headers = {
            "X-YouTube-Identity-Token": id_token,
            "Content-Type": "application/json",
        }
        async with session.post(
            f"https://www.youtube.com/youtubei/v1/upload/setthumbnail?key={api_key}",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status == 200:
                logger.debug("Thumbnail set OK")
            return True
    except Exception as e:
        logger.debug(f"Set thumbnail skipped: {e}")
        return True  # non-fatal


# ── public API ───────────────────────────────────────────────────────

async def upload_short(
    mp4_path: str | Path,
    title: str,
    description: str = "",
    cookies: list[dict] | None = None,
    visibility: str = "unlisted",
) -> tuple[bool, str]:
    """Upload a video to YouTube Shorts via HTTP-only internal API.

    Parameters
    ----------
    mp4_path : path to the .mp4 file
    title : video title (max 100 chars)
    description : description text (#Shorts added automatically if missing)
    cookies : list of cookie dicts from DB
    visibility : 'public' | 'unlisted' | 'private'

    Returns (True, "") on success, (False, "reason") on failure.
    """
    mp4_path = Path(mp4_path)
    if not mp4_path.is_file():
        return False, f"Video not found: {mp4_path}"

    if not cookies:
        return False, "No cookies provided — run /ytcookies first"

    # Ensure #Shorts in description
    desc = description.strip()
    if "#Shorts" not in desc and "#shorts" not in desc:
        desc += "\n\n#Shorts"

    file_size = mp4_path.stat().st_size
    file_name = mp4_path.name

    # ── build cookie dict for session ──
    cookie_dict = _cookie_dict(cookies)

    async with aiohttp.ClientSession(
        cookies=cookie_dict,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
        timeout=TIMEOUT,
    ) as session:
        # ── Step 1: Fetch page to get API tokens ──
        logger.info("Fetching YouTube page for API tokens…")
        api_key, id_token, client_version = await _fetch_tokens(session)
        if not id_token:
            return False, "Could not extract ID_TOKEN — session expired or invalid cookies"

        logger.info("Creating upload session…")
        session_result = await _create_upload_session(
            session, api_key, id_token, client_version or "2.20250101.00.00",
            file_size, file_name,
        )
        if not session_result:
            return False, "Failed to create upload session (check logs)"

        # Extract upload URL from response
        scotty_resource = session_result.get("scottyResourceId")
        upload_url = None
        if "uploadUrl" in session_result:
            upload_url = session_result["uploadUrl"]
        elif "url" in session_result.get("scottyResource", {}):
            upload_url = session_result["scottyResource"]["url"]

        if not upload_url and scotty_resource:
            upload_url = f"https://upload.youtube.com/upload/scotty/{scotty_resource}"

        if not upload_url:
            err = json.dumps(session_result, default=str)[:300]
            return False, f"No upload URL in response: {err}"

        # ── Step 2: Upload binary ──
        logger.info(f"Uploading binary ({file_size} bytes)…")
        upload_ok = await _upload_binary(upload_url, mp4_path)
        if not upload_ok:
            return False, "Binary upload to YouTube failed (check logs)"

        # Extract video ID from session response
        video_id = session_result.get("encryptedVideoId") or session_result.get("videoId")
        if not video_id:
            video_id = session_result.get("scottyResource", {}).get("videoId")

        if not video_id:
            return False, "Could not extract video ID from session response"

        # ── Step 3: Set metadata and publish ──
        logger.info(f"Setting metadata for video {video_id}…")
        meta_ok = await _process_pending(
            session, api_key, id_token, client_version or "2.20250101.00.00",
            video_id, title[:100], desc, visibility,
        )
        if not meta_ok:
            return False, "Failed to set video metadata (check logs)"

        # ── Step 4: Thumbnail (best-effort) ──
        await _set_thumbnail(session, api_key, id_token, client_version or "2.20250101.00.00", video_id)

        logger.info(f"✅ YouTube Shorts published: {title}")
        return True, ""


# ── direct call ──────────────────────────────────────────────────────

async def upload_video(
    mp4_path: str,
    title: str,
    description: str = "",
    cookies: list[dict] | None = None,
    visibility: str = "unlisted",
) -> tuple[bool, str]:
    """Shortcut: upload in one call."""
    return await upload_short(mp4_path, title, description, cookies, visibility)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    import sys
    if len(sys.argv) < 3:
        print("Usage: python youtube_api.py <video.mp4> <title> [description] [public|unlisted|private]")
        sys.exit(1)
    mp4 = sys.argv[1]
    title = sys.argv[2]
    desc = sys.argv[3] if len(sys.argv) > 3 else ""
    vis = sys.argv[4] if len(sys.argv) > 4 else "unlisted"
    # For CLI usage, load cookies from file
    cookies_path = Path("youtube_cookies") / "youtube_cookies.json"
    cookies = json.loads(cookies_path.read_text()) if cookies_path.exists() else None
    ok, reason = asyncio.run(upload_video(mp4, title, desc, cookies, vis))
    print(f"{'✅' if ok else '❌'} {reason if reason else 'Upload OK'}")
