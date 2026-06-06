"""
YouTube Shorts uploader via youtube-up (Internal API, cookie auth only).
Lightweight, no browser, no Playwright, ~50MB RAM.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any

from youtube_up import Metadata, PrivacyEnum, YTUploaderSession

logger = logging.getLogger("youtube_uploader")


def json_to_netscape(json_cookies: list[dict[str, Any]]) -> str:
    """Convert JSON cookie array to Netscape cookies.txt format."""
    lines = ["# Netscape HTTP Cookie File"]
    for c in json_cookies:
        domain = c.get("domain", "")
        host_only = c.get("hostOnly", False)
        # Netscape: if host_only=False (domain cookie), domain MUST start with dot and flag=TRUE
        # if host_only=True, no leading dot and flag=FALSE
        if not host_only and not domain.startswith("."):
            domain = "." + domain
        elif host_only and domain.startswith("."):
            domain = domain.lstrip(".")
        flag = "FALSE" if host_only else "TRUE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expires = str(int(c.get("expirationDate", 0))) if c.get("expirationDate") else "0"
        name = c["name"]
        value = c["value"]
        lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}")
    return "\n".join(lines)


class YouTubeUploader:
    """Upload Shorts to YouTube via youtube-up library (Internal API)."""

    def __init__(self, cookies: list[dict[str, Any]] | None = None):
        self._cookies = cookies

    async def upload_short(
        self,
        mp4_path: str | Path,
        title: str,
        description: str = "",
        visibility: str = "unlisted",
    ) -> tuple[bool, str]:
        """Upload a video to YouTube as a Short.

        Returns (True, "") on success, (False, error_msg) on failure.
        """
        mp4_path = Path(mp4_path)
        if not mp4_path.is_file():
            return False, f"File not found: {mp4_path}"
        if not self._cookies:
            return False, "No cookies provided"


        # Ensure #Shorts in description
        desc = description.strip()
        if "#Shorts" not in desc and "#shorts" not in desc:
            desc += "\n\n#Shorts"

        # Convert cookies to Netscape format and write temp file
        netscape_content = json_to_netscape(self._cookies)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(netscape_content)
            cookies_path = f.name

        try:
            uploader = YTUploaderSession.from_cookies_txt(cookies_path)

            privacy_map = {
                "public": PrivacyEnum.PUBLIC,
                "unlisted": PrivacyEnum.UNLISTED,
                "private": PrivacyEnum.PRIVATE,
            }
            privacy = privacy_map.get(visibility.lower(), PrivacyEnum.UNLISTED)

            metadata = Metadata(
                title=title[:100],
                description=desc,
                privacy=privacy,
                made_for_kids=False,
            )

            # youtube-up upload is sync — run in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: uploader.upload(str(mp4_path), metadata))

            logger.info(f"✅ Published: {title}")
            return True, ""

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Upload failed: {err_msg}")
            return False, err_msg
        finally:
            Path(cookies_path).unlink(missing_ok=True)


# ── direct call ──────────────────────────────────────────────────────

async def upload_video(mp4_path: str, title: str, description: str = "",
                       visibility: str = "unlisted") -> tuple[bool, str]:
    """Shortcut: create uploader and upload in one call."""
    up = YouTubeUploader()
    return await up.upload_short(mp4_path, title, description, visibility)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    import sys
    if len(sys.argv) < 3:
        print("Usage: python youtube_uploader.py <video.mp4> <title> [description] [public|unlisted|private]")
        sys.exit(1)
    mp4 = sys.argv[1]
    title = sys.argv[2]
    desc = sys.argv[3] if len(sys.argv) > 3 else ""
    vis = sys.argv[4] if len(sys.argv) > 4 else "unlisted"
    asyncio.run(upload_video(mp4, title, desc, vis))