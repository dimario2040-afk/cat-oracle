"""
YouTube Shorts uploader via YouTube Internal API (cookie auth).
No OAuth, no Playwright, no youtube-up.

Uses SAPISID hash authentication + YouTube InnerTube API.
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from hashlib import sha1
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger("youtube_uploader")

# Cookies required by YouTube Internal API auth
AUTH_COOKIE_NAMES = {
    "LOGIN_INFO",
    "__Secure-1PSID",
    "__Secure-3PSID",
    "__Secure-1PAPISID",
    "__Secure-3PAPISID",
    "__Secure-1PSIDTS",
    "__Secure-3PSIDTS",
    "SAPISID",
    "APISID",
    "HSID",
    "SSID",
    "SID",
    "PREF",
}

# Regexes for extracting session data from /upload page
_RE_INNERTUBE_API_KEY = re.compile(r'"INNERTUBE_API_KEY":"([^"]*)"')
_RE_SESSION_INDEX = re.compile(r'"SESSION_INDEX":"([^"]*)"')
_RE_CHANNEL_ID = re.compile(r"https://studio\.youtube\.com/channel/([^/]*)/*")
_RE_DELEGATED_SESSION_ID = re.compile(r'"DELEGATED_SESSION_ID":"([^"]*)"')

CLIENT_VERSION = "1.20231215.01.00"


def _prepare_cookies(
    raw_cookies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize cookies for upload session: fix domains, ensure SAPISID."""
    # First pass: collect all cookies, index by name
    by_name: dict[str, dict[str, Any]] = {}
    for c in raw_cookies:
        name = c.get("name", "")
        by_name.setdefault(name, c)

    # If SAPISID is missing but __Secure-3PAPISID exists, copy it
    if "SAPISID" not in by_name and "__Secure-3PAPISID" in by_name:
        sapisid = dict(by_name["__Secure-3PAPISID"])
        sapisid["name"] = "SAPISID"
        sapisid["hostOnly"] = False
        by_name["SAPISID"] = sapisid
        logger.info("Created SAPISID cookie from __Secure-3PAPISID")

    # Force domain of all auth cookies to .youtube.com so requests sends them
    out = []
    for name, c in by_name.items():
        if name in AUTH_COOKIE_NAMES:
            c = dict(c)
            c["domain"] = ".youtube.com"
            c["hostOnly"] = False
            c["path"] = "/"
        out.append(c)

    logger.info(f"Prepared {len(out)} cookies ({sum(1 for c in out if c.get('name') in AUTH_COOKIE_NAMES)} auth)")
    return out


class YouTubeCookieAuth:
    """Manages cookie-based auth for YouTube Internal API."""

    def __init__(self, cookies: list[dict[str, Any]]):
        self._session = requests.Session()
        self._setup_session(cookies)

    def _setup_session(self, raw_cookies: list[dict[str, Any]]) -> None:
        """Configure requests session with cookie jar and auth headers."""
        prepared = _prepare_cookies(raw_cookies)

        # Set cookies using http.cookiejar.Cookie for full compatibility
        from http.cookiejar import Cookie
        for c in prepared:
            name = c["name"]
            value = c["value"]
            domain = c.get("domain", ".youtube.com")
            # requests cookies use domain without leading dot
            requests_domain = domain.lstrip(".")
            cookie_obj = Cookie(
                version=0,
                name=name,
                value=value,
                port=None,
                port_specified=False,
                domain=requests_domain,
                domain_specified=True,
                domain_initial_dot=domain.startswith("."),
                path=c.get("path", "/"),
                path_specified=True,
                secure=c.get("secure", False),
                expires=None,
                discard=True,
                comment=None,
                comment_url=None,
                rest={"HttpOnly": c.get("httpOnly", False)},
                rfc2109=False,
            )
            self._session.cookies.set_cookie(cookie_obj)

        # Collect SAPISID values for all three auth schemes (like yt-dlp does)
        by_name = {c["name"]: c["value"] for c in prepared}
        sapisid = by_name.get("SAPISID") or by_name.get("__Secure-3PAPISID")
        _1papisid = by_name.get("__Secure-1PAPISID")
        _3papisid = by_name.get("__Secure-3PAPISID")

        if not sapisid:
            raise ValueError("No SAPISID or __Secure-3PAPISID cookie found")

        # Use studio.youtube.com as origin (exactly like youtube-up)
        origin = "https://studio.youtube.com"
        ts = str(int(time.time()))

        auth_parts = []
        # SAPISIDHASH (primary)
        hash1 = sha1(f"{ts} {sapisid} {origin}".encode("utf-8")).hexdigest()
        auth_parts.append(f"SAPISIDHASH {ts}_{hash1}")
        # SAPISID1PHASH (optional)
        if _1papisid:
            hash2 = sha1(f"{ts} {_1papisid} {origin}".encode("utf-8")).hexdigest()
            auth_parts.append(f"SAPISID1PHASH {ts}_{hash2}")
        # SAPISID3PHASH (optional)
        if _3papisid:
            hash3 = sha1(f"{ts} {_3papisid} {origin}".encode("utf-8")).hexdigest()
            auth_parts.append(f"SAPISID3PHASH {ts}_{hash3}")

        self._session.headers.update({
            "Authorization": " ".join(auth_parts),
            "x-origin": origin,
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })
        logger.info(f"Session configured: {len(auth_parts)} SAPISID hashes, "
                     f"{len(prepared)} cookies")

    def get(self, url: str, **kwargs) -> requests.Response:
        return self._session.get(url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self._session.post(url, **kwargs)


class YouTubeUploader:
    """Upload Shorts to YouTube via Internal API. No browser needed."""

    def __init__(self, cookies: list[dict[str, Any]] | None = None):
        self._cookies = cookies or []
        self._auth: YouTubeCookieAuth | None = None

    # ── public API ─────────────────────────────────────────────────────

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

        try:
            self._auth = YouTubeCookieAuth(self._cookies)

            # Step 1: get session data (channel_id, api_key, etc.)
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._get_session_data)

            # Step 2: get upload URL from scotty
            upload_url = await loop.run_in_executor(
                None, self._get_video_upload_url, data
            )

            # Step 3: upload video file
            scotty_id = await loop.run_in_executor(
                None, self._upload_file, upload_url, str(mp4_path)
            )

            # Step 4: create video entry
            video_id = await loop.run_in_executor(
                None, self._create_video, data, scotty_id, title, desc
            )

            if not video_id:
                return False, "Could not create video (empty response)"

            # Step 5: update metadata (privacy, title, description)
            await loop.run_in_executor(
                None, self._update_metadata, data, video_id, title, desc, visibility
            )

            logger.info(f"Published: {title} -> https://youtu.be/{video_id}")
            return True, video_id

        except Exception as e:
            err = str(e)
            logger.error(f"Upload failed: {err}")
            return False, err

    # ── internal upload flow ───────────────────────────────────────────

    def _get_session_data(self) -> dict[str, Any]:
        """GET youtube.com/upload and extract channel/auth data from page."""
        auth = self._auth
        assert auth is not None

        logger.info("Requesting youtube.com/upload to validate session...")

        # Use youtube.com without www, matching youtube-up behavior
        r = auth.get("https://youtube.com/upload", allow_redirects=True)

        logger.info(f"Response: status={r.status_code}, final_url={r.url}")
        logger.info(f"Response headers: {dict(r.headers)}")
        logger.info(f"Response body (first 500): {r.text[:500]}")

        r.raise_for_status()

        # Check we landed on studio
        if "studio.youtube.com/channel" not in r.url:
            logger.warning(f"Redirect target is NOT studio: {r.url}")
            if "accounts.google.com" in r.url:
                raise RuntimeError("Redirected to Google login - cookies expired or invalid")
            if "studio.youtube.com/channel" not in r.text:
                raise RuntimeError(
                    "Could not log in to YouTube account. Try getting new cookies"
                )

        html = r.text

        m = _RE_CHANNEL_ID.search(r.url)
        channel_id = m.group(1) if m else None
        if not channel_id:
            raise RuntimeError("Could not extract channel_id from redirect URL")

        m = _RE_INNERTUBE_API_KEY.search(html)
        api_key = m.group(1) if m else None
        if not api_key:
            raise RuntimeError("Could not extract INNERTUBE_API_KEY")

        m = _RE_SESSION_INDEX.search(html)
        authuser = m.group(1) if m else "0"

        m = _RE_DELEGATED_SESSION_ID.search(html)
        delegated_session_id = m.group(1) if m else None

        data = {
            "channel_id": channel_id,
            "api_key": api_key,
            "authuser": authuser,
            "delegated_session_id": delegated_session_id,
        }
        logger.info(f"Session data: channel={channel_id}, api_key={api_key[:8]}...")
        return data

    def _get_video_upload_url(self, data: dict) -> str:
        """Start a scotty resumable upload session, return upload URL."""
        auth = self._auth
        assert auth is not None

        frontend_id = f"innertube_studio:{str(uuid.uuid4()).upper()}:0"
        data["frontend_upload_id"] = frontend_id

        headers = {
            "x-goog-upload-command": "start",
            "x-goog-upload-protocol": "resumable",
        }
        params = {"authuser": data["authuser"]}
        body = {"frontendUploadId": frontend_id}

        r = auth.post(
            "https://upload.youtube.com/upload/studio",
            headers=headers,
            params=params,
            json=body,
        )
        r.raise_for_status()

        upload_url = r.headers.get("x-goog-upload-url")
        if not upload_url:
            raise RuntimeError("No x-goog-upload-url in response")

        logger.info(f"Got upload URL: {upload_url[:60]}...")
        return upload_url

    def _upload_file(self, upload_url: str, file_path: str) -> str:
        """Upload video binary via scotty resumable protocol."""
        auth = self._auth
        assert auth is not None

        file_size = os.path.getsize(file_path)
        headers = {
            "x-goog-upload-command": "upload, finalize",
            "x-goog-upload-offset": "0",
        }

        with open(file_path, "rb") as f:
            r = auth.post(upload_url, headers=headers, data=f)

        r.raise_for_status()
        body = r.json()
        scotty_id = body.get("scottyResourceId")
        if not scotty_id:
            raise RuntimeError(f"No scottyResourceId in response: {body}")

        logger.info(f"Uploaded to scotty: {scotty_id[:40]}...")
        return scotty_id

    def _create_video(
        self,
        data: dict,
        scotty_resource_id: str,
        title: str,
        description: str,
    ) -> str | None:
        """Create video entry via InnerTube API."""
        auth = self._auth
        assert auth is not None

        api_key = data["api_key"]
        channel_id = data["channel_id"]
        frontend_id = data["frontend_upload_id"]
        delegated_id = data.get("delegated_session_id")

        params = {"key": api_key, "alt": "json"}

        # Build the InnerTube request body
        body = {
            "channelId": channel_id,
            "context": {
                "client": {
                    "clientName": 62,
                    "clientVersion": CLIENT_VERSION,
                    "experimentsToken": "",
                    "gl": "US",
                    "hl": "en",
                    "utcOffsetMinutes": -300,
                    "userInterfaceTheme": "USER_INTERFACE_THEME_DARK",
                    "screenWidthPoints": 1920,
                    "screenHeightPoints": 529,
                    "screenPixelDensity": 1,
                    "screenDensityFloat": 1,
                },
                "request": {
                    "internalExperimentFlags": [],
                    "returnLogEntry": True,
                    "sessionInfo": {"token": ""},
                },
                "user": {
                    "delegationContext": {
                        "externalChannelId": channel_id,
                        "roleType": {
                            "channelRoleType": "CREATOR_CHANNEL_ROLE_TYPE_OWNER"
                        },
                    },
                },
            },
            "delegationContext": {
                "externalChannelId": channel_id,
                "roleType": {"channelRoleType": "CREATOR_CHANNEL_ROLE_TYPE_OWNER"},
            },
            "frontendUploadId": frontend_id,
            "initialMetadata": {
                "title": {"newTitle": title[:100]},
                "description": {"newDescription": description, "shouldSegment": True},
                "privacy": {"newPrivacy": "PRIVATE"},
                "draftState": {"isDraft": True},
                "tags": {"newTags": []},
            },
            "presumedShort": False,
            "resourceId": {"scottyResourceId": {"id": scotty_resource_id}},
        }
        # Add delegated session id if present
        if delegated_id:
            body["context"]["user"]["onBehalfOfUser"] = delegated_id

        r = auth.post(
            "https://studio.youtube.com/youtubei/v1/upload/createvideo",
            params=params,
            json=body,
        )
        r.raise_for_status()
        resp = r.json()
        video_id = resp.get("videoId")
        if video_id:
            logger.info(f"Video created: {video_id}")
        else:
            logger.warning(f"Create video response has no videoId: {resp}")
        return video_id

    def _update_metadata(
        self,
        data: dict,
        video_id: str,
        title: str,
        description: str,
        visibility: str,
    ) -> None:
        """Set video metadata (title, description, privacy)."""
        auth = self._auth
        assert auth is not None

        api_key = data["api_key"]
        channel_id = data["channel_id"]
        delegated_id = data.get("delegated_session_id")

        # Map visibility to YouTube's format
        privacy_map = {
            "public": "PUBLIC",
            "unlisted": "UNLISTED",
            "private": "PRIVATE",
        }
        privacy = privacy_map.get(visibility.lower(), "UNLISTED")

        params = {"key": api_key, "alt": "json"}

        body = {
            "context": {
                "client": {
                    "clientName": 62,
                    "clientVersion": CLIENT_VERSION,
                    "experimentsToken": "",
                    "gl": "US",
                    "hl": "en",
                    "utcOffsetMinutes": -300,
                    "userInterfaceTheme": "USER_INTERFACE_THEME_DARK",
                    "screenWidthPoints": 1920,
                    "screenHeightPoints": 529,
                    "screenPixelDensity": 1,
                    "screenDensityFloat": 1,
                },
                "request": {
                    "internalExperimentFlags": [],
                    "returnLogEntry": True,
                    "sessionInfo": {"token": ""},
                },
                "user": {
                    "delegationContext": {
                        "externalChannelId": channel_id,
                        "roleType": {
                            "channelRoleType": "CREATOR_CHANNEL_ROLE_TYPE_OWNER"
                        },
                    },
                },
            },
            "delegationContext": {
                "externalChannelId": channel_id,
                "roleType": {"channelRoleType": "CREATOR_CHANNEL_ROLE_TYPE_OWNER"},
            },
            "encryptedVideoId": video_id,
            "madeForKids": {"newMfk": "MDE_MADE_FOR_KIDS_TYPE_NOT_MFK",
                            "operation": "MDE_MADE_FOR_KIDS_UPDATE_OPERATION_SET"},
            "draftState": {"operation": "MDE_DRAFT_STATE_UPDATE_OPERATION_REMOVE_DRAFT_STATE"},
            "privacyState": {"newPrivacy": privacy},
        }
        if delegated_id:
            body["context"]["user"]["onBehalfOfUser"] = delegated_id

        r = auth.post(
            "https://studio.youtube.com/youtubei/v1/video_manager/metadata_update",
            params=params,
            json=body,
        )
        r.raise_for_status()
        logger.info(f"Metadata updated for {video_id}: privacy={privacy}")


async def upload_video(
    mp4_path: str,
    title: str,
    description: str = "",
    visibility: str = "unlisted",
    cookies: list[dict[str, Any]] | None = None,
) -> tuple[bool, str]:
    """Shortcut: create uploader and upload in one call."""
    up = YouTubeUploader(cookies=cookies)
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
    cookies_json = os.environ.get("YT_COOKIES_JSON")
    cookies = json.loads(cookies_json) if cookies_json else None
    asyncio.run(upload_video(mp4, title, desc, vis, cookies))
