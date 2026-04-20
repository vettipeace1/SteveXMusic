import os
import aiohttp
import numpy as np
from unidecode import unidecode
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from anony import config
from anony.helpers import Track


class Thumbnail:
    def __init__(self):
        self.size = (1280, 720)

        self.font_title = ImageFont.truetype(
            "anony/helpers/Raleway-Bold.ttf", 42
        )
        self.font_sub = ImageFont.truetype(
            "anony/helpers/Inter-Light.ttf", 26
        )

        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    async def save_thumb(self, path, url):
        async with self.session.get(url) as resp:
            with open(path, "wb") as f:
                f.write(await resp.read())
        return path

    def get_dominant_color(self, img):
        img = img.resize((100, 100))
        arr = np.array(img).reshape(-1, 3)
        avg = arr.mean(axis=0)
        return tuple(int(min(255, c * 1.2)) for c in avg)

    async def generate(self, song: Track):
        try:
            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}.png"

            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)

            base = Image.open(temp).convert("RGB")
            dominant = self.get_dominant_color(base)

            # Background
            bg = base.resize(self.size).filter(ImageFilter.GaussianBlur(30))
            overlay = Image.new("RGBA", self.size, (0, 0, 0, 180))
            canvas = Image.alpha_composite(bg.convert("RGBA"), overlay)

            draw = ImageDraw.Draw(canvas)

            # Center cover
            cover = base.resize((520, 380))
            mask = Image.new("L", cover.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0, 0, 420, 320), radius=25, fill=255
            )
            cover.putalpha(mask)

            cx = (1280 - 520) // 2
            cy = 100
            canvas.alpha_composite(cover, (cx, cy))

            # Bottom panel
            panel = Image.new("RGBA", (1280, 220), (0, 0, 0, 200))
            canvas.alpha_composite(panel, (0, 500))

            # Small thumbnail
            small = base.resize((90, 90))
            mask2 = Image.new("L", small.size, 0)
            ImageDraw.Draw(mask2).rounded_rectangle(
                (0, 0, 90, 90), radius=15, fill=255
            )
            small.putalpha(mask2)
            canvas.alpha_composite(small, (40, 540))

            bot_name = unidecode(getattr(config, "BOT_NAME", "Music Bot"))[:18]

            # Text
            draw.text(
                (150, 540),
                song.title[:40],
                fill="white",
                font=self.font_title,
            )

            draw.text(
                (150, 590),
                f"Played by: {bot_name} • {song.channel_name[:20]}",
                fill=(200, 200, 200),
                font=self.font_sub,
            )

            # Progress bar
            x0, x1 = 150, 1150
            y = 640

            draw.rounded_rectangle(
                (x0, y, x1, y + 8),
                radius=10,
                fill=(80, 80, 80),
            )

            prog = int(x0 + (x1 - x0) * 0.5)

            draw.rounded_rectangle(
                (x0, y, prog, y + 8),
                radius=10,
                fill=dominant,
            )

            draw.ellipse(
                (prog - 6, y - 4, prog + 6, y + 12),
                fill="white",
            )

            draw.text((x0, y + 15), "0:00", fill="white", font=self.font_sub)
            draw.text(
                (x1 - 80, y + 15),
                song.duration,
                fill="white",
                font=self.font_sub,
            )

            canvas.convert("RGB").save(output, quality=95)

            try:
                os.remove(temp)
            except:
                pass

            return output

        except Exception as e:
            print("Thumbnail Error:", e)
            return config.DEFAULT_THUMB