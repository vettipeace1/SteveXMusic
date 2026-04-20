import math
import os
import re

import aiohttp
import numpy as np
from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps,
)
from unidecode import unidecode

from anony import config
from anony.helpers import Track

# ── helpers ───────────────────────────────────────────────────────────────────

def changeImageSize(maxWidth, maxHeight, image):
    widthRatio  = maxWidth  / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth    = int(widthRatio  * image.size[0])
    newHeight   = int(heightRatio * image.size[1])
    return image.resize((newWidth, newHeight), Image.LANCZOS)


def circle(img):
    img = img.convert("RGBA")
    h, w = img.size
    mask = Image.new("L", (h, w), 0)
    ImageDraw.Draw(mask).ellipse([(0, 0), (h, w)], fill=255)
    result = Image.new("RGBA", (h, w), (0, 0, 0, 0))
    result.paste(img, mask=mask)
    return result


def clear(text, limit=45):
    words, title = text.split(" "), ""
    for w in words:
        if len(title) + len(w) < limit:
            title += " " + w
    return title.strip()


def get_dominant_color(img: Image.Image, n=4):
    """Return most vibrant dominant colour via mini k-means."""
    small  = img.convert("RGB").resize((120, 120))
    arr    = np.array(small).reshape(-1, 3).astype(float)
    np.random.seed(42)
    centers = arr[np.random.choice(len(arr), n, replace=False)]
    for _ in range(12):
        dists  = np.linalg.norm(arr[:, None] - centers[None], axis=2)
        labels = np.argmin(dists, axis=1)
        for k in range(n):
            pts = arr[labels == k]
            if len(pts):
                centers[k] = pts.mean(axis=0)
    best, best_sat = centers[0], 0
    for c in centers:
        r, g, b = c / 255.0
        mx, mn  = max(r, g, b), min(r, g, b)
        sat     = (mx - mn) / (mx + 1e-9)
        lum     = (mx + mn) / 2
        score   = sat * (1 - abs(lum - 0.5))
        if score > best_sat:
            best_sat, best = score, c
    return tuple(int(x) for x in best)


def build_palette(base):
    """
    Always return ALL 10 neon colours in a visually pleasing rainbow cycle,
    rotated so the colour closest to the song's dominant hue comes first.
    """
    RAINBOW = [
        (0x1e, 0x90, 0xff),  # Blue
        (0x06, 0xb6, 0xd4),  # Cyan
        (0x14, 0xb8, 0xa6),  # Teal
        (0x22, 0xc5, 0x5e),  # Green
        (0xf5, 0x9e, 0x0b),  # Amber
        (0xf9, 0x73, 0x16),  # Orange
        (0xf4, 0x3f, 0x5e),  # Rose
        (0xec, 0x48, 0x99),  # Pink
        (0xa8, 0x55, 0xf7),  # Purple
        (0xe2, 0xe8, 0xf0),  # White
    ]
    br, bg, bb = base

    def dist(c):
        return math.sqrt(
            (c[0] - br) ** 2 * 0.299
            + (c[1] - bg) ** 2 * 0.587
            + (c[2] - bb) ** 2 * 0.114
        )

    best_idx = min(range(len(RAINBOW)), key=lambda i: dist(RAINBOW[i]))
    return RAINBOW[best_idx:] + RAINBOW[:best_idx]


def make_neon_glow_border(size, bbox, dominant, radius=30, stroke=6, glow_layers=10):
    """
    Clean single-stroke neon border with soft glowing blur halo.
    """
    NEON = [
        (0x1e, 0x90, 0xff),
        (0x06, 0xb6, 0xd4),
        (0x14, 0xb8, 0xa6),
        (0x22, 0xc5, 0x5e),
        (0xf5, 0x9e, 0x0b),
        (0xf9, 0x73, 0x16),
        (0xf4, 0x3f, 0x5e),
        (0xec, 0x48, 0x99),
        (0xa8, 0x55, 0xf7),
        (0xe2, 0xe8, 0xf0),
    ]
    br, bg, bb = dominant

    def dist(c):
        return math.sqrt(
            (c[0] - br) ** 2 * 0.299
            + (c[1] - bg) ** 2 * 0.587
            + (c[2] - bb) ** 2 * 0.114
        )

    sorted_neon = sorted(NEON, key=dist)
    nr,  ng,  nb  = sorted_neon[0]
    nr2, ng2, nb2 = sorted_neon[1]

    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    x0, y0, x1, y1 = bbox
    ld = ImageDraw.Draw(layer)

    # Outer soft glow halo
    for i in range(glow_layers, 0, -1):
        t      = i / glow_layers
        expand = int(t ** 0.5 * glow_layers * 4)
        alpha  = int(4 + (1 - t) ** 1.2 * 140)
        w      = stroke + int(t * glow_layers * 2)
        lx0    = max(0,       x0 - expand)
        ly0    = max(0,       y0 - expand)
        lx1    = min(size[0], x1 + expand)
        ly1    = min(size[1], y1 + expand)
        cr, cg, cb = (nr, ng, nb) if i % 2 == 0 else (nr2, ng2, nb2)
        ld.rounded_rectangle(
            (lx0, ly0, lx1, ly1),
            radius=max(6, radius - expand // 6),
            outline=(cr, cg, cb, alpha),
            width=w,
        )

    # Bright inner glow
    for s in range(4, 0, -1):
        alpha = 60 + s * 35
        ld.rounded_rectangle(
            (x0 - s, y0 - s, x1 + s, y1 + s),
            radius=radius,
            outline=(
                min(255, nr + 60),
                min(255, ng + 60),
                min(255, nb + 60),
                alpha,
            ),
            width=stroke + s,
        )

    # Crisp primary stroke
    ld.rounded_rectangle(
        bbox,
        radius=radius,
        outline=(min(255, nr + 90), min(255, ng + 90), min(255, nb + 90), 255),
        width=stroke,
    )

    # White-hot centre line
    ld.rounded_rectangle(
        bbox,
        radius=radius,
        outline=(255, 255, 255, 90),
        width=max(1, stroke // 3),
    )

    return layer


def draw_glowing_progress_bar(draw, canvas, x0, y0, x1, bar_h, thumb_frac, palette):
    """
    Draw a neon-glowing progress bar whose colour matches the border palette.
    """
    # Track background
    draw.rounded_rectangle(
        [(x0, y0), (x1, y0 + bar_h)],
        radius=bar_h // 2,
        fill=(50, 50, 80, 160),
    )

    thumb_x  = int(x0 + (x1 - x0) * thumb_frac)
    base_col = palette[0]
    accent   = palette[3]

    # Glow behind filled bar
    for glow in range(6, 0, -1):
        gr, gg, gb = base_col
        ga         = int(15 + (6 - glow) * 18)
        gpad       = glow * 2
        draw.rounded_rectangle(
            [(x0, y0 - gpad // 2), (thumb_x, y0 + bar_h + gpad // 2)],
            radius=bar_h // 2 + gpad // 2,
            fill=(min(255, gr + 60), min(255, gg + 60), min(255, gb + 60), ga),
        )

    # Filled (played) bar
    r1, g1, b1 = base_col
    r2, g2, b2 = accent
    draw.rounded_rectangle(
        [(x0, y0), (thumb_x, y0 + bar_h)],
        radius=bar_h // 2,
        fill=(min(255, r1 + 80), min(255, g1 + 80), min(255, b1 + 80), 240),
    )
    # Thin bright top highlight stripe
    draw.rounded_rectangle(
        [(x0, y0), (thumb_x, y0 + bar_h // 3)],
        radius=bar_h // 2,
        fill=(min(255, r2 + 100), min(255, g2 + 100), min(255, b2 + 100), 120),
    )

    # Thumb dot glow
    TR = 10
    cy = y0 + bar_h // 2
    for glow in range(5, 0, -1):
        gr, gg, gb = accent
        ga         = int(20 + (5 - glow) * 25)
        gr_r       = TR + glow * 3
        draw.ellipse(
            [(thumb_x - gr_r, cy - gr_r), (thumb_x + gr_r, cy + gr_r)],
            fill=(min(255, gr + 80), min(255, gg + 80), min(255, gb + 80), ga),
        )
    # Solid bright dot
    draw.ellipse(
        [(thumb_x - TR, cy - TR), (thumb_x + TR, cy + TR)],
        fill=(255, 255, 255, 250),
    )
    # Inner coloured core
    draw.ellipse(
        [(thumb_x - TR + 3, cy - TR + 3), (thumb_x + TR - 3, cy + TR - 3)],
        fill=(min(255, r2 + 100), min(255, g2 + 100), min(255, b2 + 100), 200),
    )

    return thumb_x


# ── Thumbnail class ───────────────────────────────────────────────────────────

class Thumbnail:
    def __init__(self):
        self.rect    = (914, 514)
        self.fill    = (255, 255, 255)
        self.mask    = Image.new("L", self.rect, 0)
        # Fonts (used as fallback / badge text)
        try:
            self.font1 = ImageFont.truetype("anony/helpers/Raleway-Bold.ttf", 30)
            self.font2 = ImageFont.truetype("anony/helpers/Inter-Light.ttf", 30)
        except Exception:
            self.font1 = self.font2 = ImageFont.load_default()
        self.session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self.session:
            await self.session.close()

    async def save_thumb(self, output_path: str, url: str) -> str:
        async with self.session.get(url) as resp:
            with open(output_path, "wb") as f:
                f.write(await resp.read())
        return output_path

    async def generate(self, song: Track, size=(1280, 720)) -> str:
        """
        Generate a styled now-playing thumbnail with neon glow effects.

        Uses song.id, song.thumbnail, song.title, song.duration,
        song.channel_name, song.view_count.
        """
        output = f"cache/{song.id}.png"
        if os.path.exists(output):
            return output

        try:
            temp = f"cache/temp_{song.id}.jpg"
            await self.save_thumb(temp, song.thumbnail)

            # Sanitise metadata
            title    = re.sub(r"\W+", " ", str(song.title)).title()
            duration = str(song.duration) if song.duration else "Unknown"
            channel  = str(song.channel_name) if song.channel_name else "Unknown Channel"
            views    = str(song.view_count)   if song.view_count   else "Unknown Views"
            bot_name = unidecode(
                getattr(config, "BOT_NAME", None) or "Music Bot"
            )[:18]

            # ── Work at 2× resolution for crisp anti-aliasing ──────────────
            SCALE    = 2
            W, H     = 1280 * SCALE, 720 * SCALE
            BOTTOM_H = 185 * SCALE
            CZ_H     = H - BOTTOM_H

            canvas = Image.new("RGBA", (W, H), (10, 6, 22, 255))

            # Load & enhance source image
            cover_raw = Image.open(temp).convert("RGBA")
            cover_raw = ImageEnhance.Sharpness(cover_raw).enhance(1.4)
            cover_raw = ImageEnhance.Color(cover_raw).enhance(1.3)

            dominant  = get_dominant_color(cover_raw)
            palette   = build_palette(dominant)
            r_d, g_d, b_d = dominant

            # Blurred cover background
            cover_bg = cover_raw.resize((W, CZ_H), Image.LANCZOS).convert("RGBA")
            cover_bg = cover_bg.filter(ImageFilter.GaussianBlur(28 * SCALE // 2))
            cover_bg = Image.alpha_composite(
                cover_bg, Image.new("RGBA", (W, CZ_H), (0, 0, 0, 140))
            )
            canvas.paste(cover_bg, (0, 0))

            # Gradient fade at bottom of cover zone
            fade = Image.new("RGBA", (W, 130 * SCALE), (0, 0, 0, 0))
            for row in range(130 * SCALE):
                a = int((row / (130 * SCALE)) ** 1.5 * 240)
                ImageDraw.Draw(fade).line([(0, row), (W, row)], fill=(10, 6, 22, a))
            canvas.alpha_composite(fade, (0, CZ_H - 65 * SCALE))

            # Bottom bar
            bar_r = max(0, r_d - 160)
            bar_g = max(0, g_d - 160)
            bar_b = max(0, b_d - 150)
            bar   = Image.new(
                "RGBA", (W, BOTTOM_H + 20 * SCALE), (bar_r, bar_g, bar_b, 240)
            )
            bar = Image.alpha_composite(
                bar,
                Image.new("RGBA", (W, BOTTOM_H + 20 * SCALE), (0, 0, 0, 80)),
            )
            canvas.alpha_composite(bar, (0, CZ_H - 16 * SCALE))

            # Centre cover art
            CV_W    = 390 * SCALE
            CV_H    = 320 * SCALE
            CV_LEFT = (W - CV_W) // 2
            CV_TOP  = (CZ_H - CV_H) // 2 + 30 * SCALE

            cover_sq = cover_raw.resize((CV_W, CV_H), Image.LANCZOS).convert("RGBA")
            cover_sq = ImageEnhance.Sharpness(cover_sq).enhance(1.5)
            cover_sq = ImageEnhance.Contrast(cover_sq).enhance(1.1)
            rc_mask  = Image.new("L", (CV_W, CV_H), 0)
            ImageDraw.Draw(rc_mask).rounded_rectangle(
                [(0, 0), (CV_W, CV_H)], radius=22 * SCALE, fill=255
            )
            cover_sq.putalpha(rc_mask)

            # Drop shadow
            sh_w, sh_h = CV_W + 80 * SCALE, CV_H + 80 * SCALE
            shadow     = Image.new("RGBA", (sh_w, sh_h), (0, 0, 0, 0))
            ImageDraw.Draw(shadow).rounded_rectangle(
                [
                    (24 * SCALE, 24 * SCALE),
                    (sh_w - 24 * SCALE, sh_h - 24 * SCALE),
                ],
                radius=30 * SCALE,
                fill=(r_d // 2, g_d // 2, b_d // 2, 180),
            )
            shadow = shadow.filter(ImageFilter.GaussianBlur(22 * SCALE // 2))
            canvas.alpha_composite(shadow, (CV_LEFT - 40 * SCALE, CV_TOP - 40 * SCALE))
            canvas.alpha_composite(cover_sq, (CV_LEFT, CV_TOP))

            # Neon ring around cover art
            ring_pad   = 10 * SCALE
            ring_layer = make_neon_glow_border(
                (W, H),
                (
                    CV_LEFT - ring_pad,
                    CV_TOP  - ring_pad,
                    CV_LEFT + CV_W + ring_pad,
                    CV_TOP  + CV_H + ring_pad,
                ),
                dominant,
                radius=28 * SCALE,
                stroke=5 * SCALE,
                glow_layers=10,
            )
            canvas.alpha_composite(ring_layer)

            # Outer card border
            border_layer = make_neon_glow_border(
                (W, H),
                (6 * SCALE, 6 * SCALE, W - 6 * SCALE, H - 6 * SCALE),
                dominant,
                radius=30 * SCALE,
                stroke=5 * SCALE,
                glow_layers=12,
            )
            canvas.alpha_composite(border_layer)

            # ── "NOW PLAYING" badge (top-left) ────────────────────────────
            BW, BH = 210 * SCALE, 42 * SCALE
            badge  = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
            p0     = palette[0]
            ImageDraw.Draw(badge).rounded_rectangle(
                [(0, 0), (BW, BH)],
                radius=BH // 2,
                fill=(
                    max(0, p0[0] - 80),
                    max(0, p0[1] - 80),
                    max(0, p0[2] - 80),
                    210,
                ),
                outline=(
                    min(255, p0[0] + 100),
                    min(255, p0[1] + 100),
                    min(255, p0[2] + 100),
                    220,
                ),
                width=3 * SCALE // 2,
            )
            canvas.alpha_composite(badge, (28 * SCALE, 26 * SCALE))

            # ── Bot name badge (top-right) ────────────────────────────────
            try:
                font_badge_tmp = ImageFont.truetype(
                    "anony/helpers/Raleway-Bold.ttf", 18 * SCALE
                )
                txt_w = font_badge_tmp.getlength(bot_name)
            except Exception:
                txt_w = len(bot_name) * 11 * SCALE
            RBW    = int(txt_w) + 36 * SCALE
            RBH    = BH
            rbadge = Image.new("RGBA", (RBW, RBH), (0, 0, 0, 0))
            ImageDraw.Draw(rbadge).rounded_rectangle(
                [(0, 0), (RBW, RBH)],
                radius=RBH // 2,
                fill=(
                    max(0, p0[0] - 80),
                    max(0, p0[1] - 80),
                    max(0, p0[2] - 80),
                    210,
                ),
                outline=(
                    min(255, p0[0] + 100),
                    min(255, p0[1] + 100),
                    min(255, p0[2] + 100),
                    220,
                ),
                width=3 * SCALE // 2,
            )
            RB_X = W - RBW - 28 * SCALE
            RB_Y = 26 * SCALE
            canvas.alpha_composite(rbadge, (RB_X, RB_Y))

            # ── Fonts ─────────────────────────────────────────────────────
            try:
                font_bold  = ImageFont.truetype(
                    "anony/helpers/Raleway-Bold.ttf", 32 * SCALE
                )
                font_badge = ImageFont.truetype(
                    "anony/helpers/Raleway-Bold.ttf", 18 * SCALE
                )
                font_small = ImageFont.truetype(
                    "anony/helpers/Inter-Light.ttf", 24 * SCALE
                )
                font_dur   = ImageFont.truetype(
                    "anony/helpers/Inter-Light.ttf", 22 * SCALE
                )
            except Exception:
                font_bold = font_badge = font_small = font_dur = (
                    ImageFont.load_default()
                )

            draw = ImageDraw.Draw(canvas)

            # Badge texts
            draw.text(
                (48 * SCALE, 34 * SCALE),
                "NOW PLAYING",
                fill=(230, 235, 255, 245),
                font=font_badge,
            )
            draw.text(
                (RB_X + 18 * SCALE, RB_Y + (RBH - font_badge.size) // 2),
                bot_name,
                fill=(230, 235, 255, 245),
                font=font_badge,
            )

            # ── Bottom bar content ────────────────────────────────────────
            BAR_Y  = CZ_H - 16 * SCALE
            IS     = 118 * SCALE
            ICON_X = 52 * SCALE
            ICON_Y = BAR_Y + (BOTTOM_H - IS) // 2

            # Thumbnail icon
            icon_img = cover_raw.resize((IS, IS), Image.LANCZOS).convert("RGBA")
            icon_img = ImageEnhance.Sharpness(icon_img).enhance(1.3)
            ic_mask  = Image.new("L", (IS, IS), 0)
            ImageDraw.Draw(ic_mask).rounded_rectangle(
                [(0, 0), (IS, IS)], radius=16 * SCALE, fill=255
            )
            icon_img.putalpha(ic_mask)
            canvas.alpha_composite(icon_img, (ICON_X, ICON_Y))

            # Text columns
            TEXT_X  = ICON_X + IS + 22 * SCALE
            LINE1_Y = BAR_Y + 16 * SCALE
            LINE2_Y = BAR_Y + 16 * SCALE + 38 * SCALE

            draw.text(
                (TEXT_X, LINE1_Y),
                clear(title, 40),
                fill=(255, 255, 255, 250),
                font=font_bold,
            )
            draw.text(
                (TEXT_X, LINE2_Y),
                f"Played by: {bot_name}  ·  {channel[:32]}",
                fill=(175, 180, 215, 195),
                font=font_small,
            )

            # Progress bar
            PROG_X0  = TEXT_X
            PROG_X1  = W - 32 * SCALE
            BAR_H_PX = 8 * SCALE
            PROG_Y   = BAR_Y + BOTTOM_H - 52 * SCALE
            TIME_Y   = PROG_Y + BAR_H_PX + 8 * SCALE

            draw_glowing_progress_bar(
                draw,
                canvas,
                PROG_X0,
                PROG_Y,
                PROG_X1,
                BAR_H_PX,
                thumb_frac=0.65,
                palette=palette,
            )

            # Time labels
            draw.text(
                (PROG_X0, TIME_Y),
                "0:01",
                fill=(195, 200, 230, 210),
                font=font_dur,
            )
            draw.text(
                (PROG_X1 - 74 * SCALE, TIME_Y),
                duration[:7],
                fill=(195, 200, 230, 210),
                font=font_dur,
            )

            # ── Downsample to final 1280×720 ──────────────────────────────
            final = canvas.convert("RGB").resize((1280, 720), Image.LANCZOS)
            final.save(output, quality=97, optimize=False)

            # Clean up temp file
            try:
                os.remove(temp)
            except Exception:
                pass

            return output

        except Exception:
            return config.DEFAULT_THUMB