# 🔥 Ultimate YouTube Handler (Auto Cookies + Retry + Anti-Bot)

import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch
from anony import logger
from anony.helpers import Track, utils


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookie_dir = "anony/cookies"
        self.cookies = []
        self.checked = False

        # Rotate user agents (ANTI BOT)
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Linux; Android 11)",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
        ]

        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)"
        )

    # ─────────────────────────────────────────────
    # 🍪 AUTO LOAD COOKIES
    # ─────────────────────────────────────────────
    def get_cookies(self):
        if not self.checked:
            if os.path.exists(self.cookie_dir):
                for file in os.listdir(self.cookie_dir):
                    if file.endswith(".txt"):
                        self.cookies.append(os.path.join(self.cookie_dir, file))
            self.checked = True

        if not self.cookies:
            logger.warning("⚠️ No cookies found, using fallback mode")
            return None

        return random.choice(self.cookies)

    # ─────────────────────────────────────────────
    # 🔄 AUTO DOWNLOAD COOKIES FROM LINKS
    # ─────────────────────────────────────────────
    async def save_cookies(self, urls: list[str]):
        os.makedirs(self.cookie_dir, exist_ok=True)

        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    name = url.split("/")[-1]
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            with open(f"{self.cookie_dir}/{name}.txt", "wb") as f:
                                f.write(data)
                            logger.info(f"✅ Cookie saved: {name}")
                except Exception as e:
                    logger.warning(f"❌ Cookie download failed: {e}")

    # ─────────────────────────────────────────────
    # 🔍 SEARCH
    # ─────────────────────────────────────────────
    async def search(self, query: str, m_id: int, video=False):
        try:
            res = await VideosSearch(query, limit=1).next()
            if not res["result"]:
                return None

            data = res["result"][0]

            return Track(
                id=data["id"],
                title=data["title"][:30],
                channel_name=data["channel"]["name"],
                duration=data["duration"],
                duration_sec=utils.to_seconds(data["duration"]),
                thumbnail=data["thumbnails"][-1]["url"].split("?")[0],
                url=data["link"],
                view_count=data.get("viewCount", {}).get("short"),
                message_id=m_id,
                video=video
            )
        except Exception:
            return None

    # ─────────────────────────────────────────────
    # 📥 DOWNLOAD WITH AUTO RETRY + COOKIE ROTATION
    # ─────────────────────────────────────────────
    async def download(self, video_id: str, video=False):
        url = self.base + video_id
        ext = "mp4" if video else "webm"
        filename = f"downloads/{video_id}.{ext}"

        if Path(filename).exists():
            return filename

        # 🔁 Retry system
        for attempt in range(4):
            cookie = self.get_cookies()
            ua = random.choice(self.user_agents)

            ydl_opts = {
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "quiet": True,
                "noplaylist": True,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "cookiefile": cookie,
                "http_headers": {
                    "User-Agent": ua,
                    "Accept-Language": "en-US,en;q=0.9"
                }
            }

            # 🎥 Video / 🎵 Audio
            if video:
                ydl_opts["format"] = "bestvideo[height<=720]+bestaudio"
                ydl_opts["merge_output_format"] = "mp4"
            else:
                ydl_opts["format"] = "bestaudio[ext=webm]/bestaudio"

            def _download():
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    return filename
                except Exception as e:
                    logger.warning(f"⚠️ Attempt {attempt+1} failed: {e}")
                    return None

            result = await asyncio.to_thread(_download)

            if result:
                logger.info("✅ Download success")
                return result

            await asyncio.sleep(2)  # wait before retry

        logger.error("❌ All download attempts failed")
        return None

    # ─────────────────────────────────────────────
    # 📜 PLAYLIST
    # ─────────────────────────────────────────────
    async def playlist(self, limit, user, url, video):
        tracks = []
        try:
            plist = await Playlist.get(url)

            for data in plist["videos"][:limit]:
                tracks.append(
                    Track(
                        id=data["id"],
                        title=data["title"][:30],
                        channel_name=data["channel"]["name"],
                        duration=data["duration"],
                        duration_sec=utils.to_seconds(data["duration"]),
                        thumbnail=data["thumbnails"][-1]["url"].split("?")[0],
                        url=data["link"],
                        user=user,
                        video=video
                    )
                )
        except Exception:
            pass

        return tracks