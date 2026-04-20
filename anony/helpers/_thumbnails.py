# Copyright (c) 2025 AnonymousX1025
# Upgraded Premium Thumbnail Generator

import os
import aiohttp
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from unidecode import unidecode

from anony import config
from anony.helpers import Track


class Thumbnail:
    def __init__(self):
        self.size = (1280, 720)

        # Fonts (make sure these exist)
        self.font_title = ImageFont.truetype("anony/helpers/Raleway-Bold.ttf", 46)
        self.font_sub   = ImageFont.truetype("anony/helpers/Inter-Light.ttf", 28)

        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        await self.session.close()

    async def save_thumb(self, path, url):
        async with self.session.get(url) as resp:
            with open(path, "wb") as f:
                f.write(await resp.read())
        return path

    # 🎨 AUTO COLOR (Spotify-style)
    def get_dominant_color(self, img):
        img = img.resize((100, 100))
        arr = np.array(img).reshape(-1, 3)
        avg = arr.mean(axis=0)
        return tuple(int(min(255, c * 1.2)) for c in avg)

    # 🌈 NEON BORDER
    def neon_border(self, canvas, bbox, color):
        draw = ImageDraw.Draw(canvas)
        r, g, b = color

        # Glow layers
        for i in range(12, 0, -1):
            alpha = int(20 + i * 12)
            draw.rounded_rectangle(
                [bbox[0]-i, bbox[1]-i, bbox[2]+i, bbox[3]+i],
                radius=30,
                outline=(r, g, b, alpha),
                width=2
            )

        # Core white line
        draw.rounded_rectangle(
            bbox, radius=30,
            outline=(255, 255, 255, 120),
            width=2
        )

    # 🔥 TOP BADGES (NOW PLAYING + BOT NAME)
    def draw_top_badges(self, canvas, dominant, bot_name):
        draw = ImageDraw.Draw(canvas)
        r, g, b = dominant

        font = self.font_sub

        # LEFT BADGE
        text1 = "NOW PLAYING"
        w1 = int(font.getlength(text1)) + 40
        h = 48

        badge1 = Image.new("RGBA", (w1, h), (0,0,0,0))
        d1 = ImageDraw.Draw(badge1)

        d1.rounded_rectangle(
            (0,0,w1,h),
            radius=24,
            fill=(r//2, g//2, b//2, 220),
            outline=(min(255,r+100), min(255,g+100), min(255,b+100), 255),
            width=2
        )

        d1.text((20,10), text1, font=font, fill=(255,255,255))
        canvas.alpha_composite(badge1, (30, 30))

        # RIGHT BADGE (BOT NAME)
        text2 = bot_name
        w2 = int(font.getlength(text2)) + 40

        badge2 = Image.new("RGBA", (w2, h), (0,0,0,0))
        d2 = ImageDraw.Draw(badge2)

        d2.rounded_rectangle(
            (0,0,w2,h),
            radius=24,
            fill=(r//2, g//2, b//2, 220),
            outline=(min(255,r+100), min(255,g+100), min(255,b+100), 255),
            width=2
        )

        d2.text((20,10), text2, font=font, fill=(255,255,255))
        canvas.alpha_composite(badge2, (1280 - w2 - 30, 30))

    async def generate(self, song: Track):
        try:
            temp   = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}.png"

            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)

            base = Image.open(temp).convert("RGB")
            dominant = self.get_dominant_color(base)

            # 🔥 BACKGROUND
            bg = base.resize(self.size).filter(ImageFilter.GaussianBlur(30))

            # Ambient color glow
            ambient = Image.new("RGBA", self.size, (*dominant, 80))
            bg = Image.alpha_composite(bg.convert("RGBA"), ambient)

            # Dark overlay
            dark = Image.new("RGBA", self.size, (0,0,0,140))
            bg = Image.alpha_composite(bg, dark)

            canvas = bg.copy()

            # 🎵 COVER
            cover = base.resize((420, 320))
            mask = Image.new("L", cover.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle(
                (0,0,cover.size[0],cover.size[1]), radius=30, fill=255
            )
            cover.putalpha(mask)

            cx = (1280 - 420)//2
            cy = 120

            # Glow shadow
            shadow = Image.new("RGBA", (440,340), (0,0,0,0))
            ImageDraw.Draw(shadow).rounded_rectangle(
                (10,10,430,330),
                radius=35,
                fill=(*dominant,120)
            )
            shadow = shadow.filter(ImageFilter.GaussianBlur(25))

            canvas.alpha_composite(shadow, (cx-10, cy-10))
            canvas.alpha_composite(cover, (cx, cy))

            # Neon border
            self.neon_border(canvas, (cx, cy, cx+420, cy+320), dominant)

            draw = ImageDraw.Draw(canvas)

            # 🔥 BOT NAME AUTO
            bot_name = unidecode(getattr(config, "BOT_NAME", "My Music"))[:18]

            # Top badges
            self.draw_top_badges(canvas, dominant, bot_name)

            # 🎶 TEXT
            draw.text((640, 470), song.title[:40],
                      anchor="mm", fill="white", font=self.font_title)

            draw.text((640, 520),
                      f"{song.channel_name[:30]}",
                      anchor="mm", fill=(200,200,200),
                      font=self.font_sub)

            # 🎧 PROGRESS BAR
            x0, x1 = 200, 1080
            y = 600

            draw.rounded_rectangle((x0,y,x1,y+10), radius=10, fill=(80,80,80))

            prog = int(x0 + (x1-x0)*0.5)

            draw.rounded_rectangle((x0,y,prog,y+10),
                                   radius=10,
                                   fill=dominant)

            # Glow dot
            for i in range(6):
                draw.ellipse((prog-10-i, y-5-i, prog+10+i, y+15+i),
                             fill=(*dominant, 30))

            draw.ellipse((prog-8,y-5,prog+8,y+15), fill="white")

            # Time
            draw.text((x0, y+20), "0:00", fill="white", font=self.font_sub)
            draw.text((x1-80, y+20), song.duration, fill="white", font=self.font_sub)

            canvas.convert("RGB").save(output, quality=95)

            try:
                os.remove(temp)
            except:
                pass

            return output

        except Exception:
            return config.DEFAULT_THUMB