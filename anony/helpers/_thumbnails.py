# FIXED PREMIUM THUMBNAIL CODE

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

        self.font_title = ImageFont.truetype("anony/helpers/Raleway-Bold.ttf", 46)
        self.font_sub   = ImageFont.truetype("anony/helpers/Inter-Light.ttf", 28)

        self.session = None

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

    # 🎨 dominant color
    def get_dominant_color(self, img):
        img = img.resize((100, 100))
        arr = np.array(img).reshape(-1, 3)
        avg = arr.mean(axis=0)
        return tuple(int(min(255, c * 1.2)) for c in avg)

    # 🌈 neon border
    def neon_border(self, canvas, bbox, color):
        draw = ImageDraw.Draw(canvas)
        r, g, b = color

        for i in range(12, 0, -1):
            alpha = int(20 + i * 12)
            draw.rounded_rectangle(
                [bbox[0]-i, bbox[1]-i, bbox[2]+i, bbox[3]+i],
                radius=30,
                outline=(r, g, b, alpha),
                width=2
            )

        draw.rounded_rectangle(
            bbox, radius=30,
            outline=(255, 255, 255, 120),
            width=2
        )

    # 🔥 badges
    def draw_top_badges(self, canvas, dominant, bot_name):
        draw = ImageDraw.Draw(canvas)
        r, g, b = dominant

        font = self.font_sub

        # LEFT
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

        # RIGHT
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

    # 🚀 MAIN GENERATOR
    async def generate(self, song: Track):
    try:
        temp = f"cache/temp_{song.id}.jpg"
        output = f"cache/{song.id}.png"

        if os.path.exists(output):
            return output

        await self.save_thumb(temp, song.thumbnail)

        base = Image.open(temp).convert("RGB")
        dominant = self.get_dominant_color(base)

        # 🎯 BACKGROUND
        bg = base.resize(self.size).filter(ImageFilter.GaussianBlur(35))
        dark = Image.new("RGBA", self.size, (0, 0, 0, 180))
        canvas = Image.alpha_composite(bg.convert("RGBA"), dark)

        draw = ImageDraw.Draw(canvas)

        # 🎵 CENTER COVER
        cover = base.resize((420, 320))
        mask = Image.new("L", cover.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, 420, 320), radius=25, fill=255
        )
        cover.putalpha(mask)

        cx = (1280 - 420) // 2
        cy = 120

        # Glow shadow
        glow = Image.new("RGBA", (460, 360), (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle(
            (20, 20, 440, 340),
            radius=30,
            fill=(*dominant, 120)
        )
        glow = glow.filter(ImageFilter.GaussianBlur(25))

        canvas.alpha_composite(glow, (cx - 20, cy - 20))
        canvas.alpha_composite(cover, (cx, cy))

        # 🔥 NEON BORDER
        self.neon_border(canvas, (cx, cy, cx + 420, cy + 320), dominant)

        # 🎯 TOP BADGES
        bot_name = unidecode(getattr(config, "BOT_NAME", "『ꜱᴛᴇᴠᴇ'ꜱ ᴍᴜꜱɪᴄ ʙᴏᴛ 』"))[:18]
        self.draw_top_badges(canvas, dominant, bot_name)

        # =====================================
        # 🔥 BOTTOM GLASS PANEL (MAIN FIX)
        # =====================================
        panel = Image.new("RGBA", (1280, 220), (0, 0, 0, 180))
        canvas.alpha_composite(panel, (0, 500))

        draw = ImageDraw.Draw(canvas)

        # 🎵 SMALL THUMB (LEFT)
        small = base.resize((90, 90))
        mask2 = Image.new("L", small.size, 0)
        ImageDraw.Draw(mask2).rounded_rectangle(
            (0, 0, 90, 90), radius=15, fill=255
        )
        small.putalpha(mask2)
        canvas.alpha_composite(small, (40, 540))

        # 🎶 TEXTS
        draw.text((150, 540),
                  song.title[:40],
                  fill="white",
                  font=self.font_title)

        draw.text((150, 590),
                  f"Played by: {bot_name}  •  {song.channel_name[:20]}",
                  fill=(200, 200, 200),
                  font=self.font_sub)

        # =====================================
        # 🎧 PROGRESS BAR (GRADIENT STYLE)
        # =====================================
        x0, x1 = 150, 1150
        y = 640

        # background line
        draw.rounded_rectangle((x0, y, x1, y + 8),
                               radius=10,
                               fill=(80, 80, 80))

        # progress
        prog = int(x0 + (x1 - x0) * 0.5)

        # gradient effect
        for i in range(x0, prog):
            ratio = (i - x0) / (prog - x0 + 1)
            r = int(dominant[0] * ratio + 100)
            g = int(dominant[1] * ratio + 100)
            b = int(dominant[2] * ratio + 100)
            draw.line([(i, y), (i, y + 8)], fill=(r, g, b))

        # knob
        draw.ellipse((prog - 6, y - 4, prog + 6, y + 12),
                     fill="white")

        # time text
        draw.text((x0, y + 15), "0:00", fill="white", font=self.font_sub)
        draw.text((x1 - 80, y + 15), song.duration,
                  fill="white", font=self.font_sub)

        # SAVE
        canvas.convert("RGB").save(output, quality=95)

        try:
            os.remove(temp)
        except:
            pass

        return output

    except Exception as e:
        print("THUMB ERROR:", e)
        return config.DEFAULT_THUMB