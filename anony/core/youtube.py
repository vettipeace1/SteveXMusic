# Copyright (c) 2025 AnonymousX1025

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
        self.cookies = []
        self.checked = False
        self.cookie_dir = "anony/cookies"
        self.warned = False

        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)"
        )

        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=PL[A-Za-z0-9_-]+))"
        )

    # ─────────────────────────────
    # 🍪 COOKIES SYSTEM
    # ─────────────────────────────
    def get_cookies(self):
        if not self.checked:
            if os.path.exists(self.cookie_dir):
                for file in os.listdir(self.cookie_dir):
                    if file.endswith(".txt"):
                        self.cookies.append(f"{self.cookie_dir}/{file}")
            self.checked = True

        if not self.cookies:
            if not self.warned:
                logger.warning("⚠️ No cookies found")
                self.warned = True
            return None

        return random.choice(self.cookies)

    # ─────────────────────────────
    # 🔍 SEARCH
    # ─────────────────────────────
    async def search(self, query: str, m_id: int, video: bool = False):
        try:
            results = await VideosSearch(query, limit=1).next()
        except Exception:
            return None

        if results and results["result"]:
            data = results["result"][0]

            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=data.get("title")[:40],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )
        return None

    # ─────────────────────────────
    # 📂 PLAYLIST
    # ─────────────────────────────
    async def playlist(self, limit: int, user: str, url: str, video: bool):
        tracks = []
        try:
            plist = await Playlist.get(url)

            for data in plist["videos"][:limit]:
                tracks.append(
                    Track(
                        id=data.get("id"),
                        channel_name=data.get("channel", {}).get("name", ""),
                        duration=data.get("duration"),
                        duration_sec=utils.to_seconds(data.get("duration")),
                        title=data.get("title")[:40],
                        thumbnail=data.get("thumbnails")[-1].get("url").split("?")[0],
                        url=data.get("link").split("&list=")[0],
                        user=user,
                        view_count="",
                        video=video,
                    )
                )
        except Exception:
            pass

        return tracks

    # ─────────────────────────────
    # ⚡ FAST STREAM (NO DOWNLOAD)
    # ─────────────────────────────
    async def stream(self, video_id: str):
        url = self.base + video_id

        def _extract():
            try:
                ydl_opts = {
                    "quiet": True,
                    "format": "bestaudio/best",
                    "cookiefile": self.get_cookies(),
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return info.get("url")
            except Exception as e:
                logger.error(f"Stream error: {e}")
                return None

        return await asyncio.to_thread(_extract)

    # ─────────────────────────────
    # 📥 DOWNLOAD (STABLE)
    # ─────────────────────────────
    async def download(self, video_id: str, video: bool = False):
        url = self.base + video_id
        ext = "mp4" if video else "webm"
        filename = f"downloads/{video_id}.{ext}"

        if Path(filename).exists():
            return filename

        for attempt in range(3):
            cookie = self.get_cookies()

            base_opts = {
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "quiet": True,
                "noplaylist": True,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "cookiefile": cookie,
                "http_headers": {"User-Agent": "Mozilla/5.0"},
                "retries": 3,
                "fragment_retries": 3,
            }

            if video:
                ydl_opts = {
                    **base_opts,
                    "format": "bestvideo+bestaudio/best",
                    "merge_output_format": "mp4",
                }
            else:
                ydl_opts = {
                    **base_opts,
                    "format": "bestaudio/best",
                }

            def _download():
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    return filename
                except Exception as e:
                    logger.warning(f"Attempt {attempt+1} failed: {e}")
                    return None

            result = await asyncio.to_thread(_download)

            if result:
                return result

            await asyncio.sleep(2)

        logger.error("❌ Download failed after retries")
        return None