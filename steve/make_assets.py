"""make_assets.py - textures for the Steve subscribe animation (block faces with Arabic text, nametags). Run: python make_assets.py"""
import os
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

H = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(H, "tex")
FONT = os.environ.get("STEVE_FONT", r"C:\Windows\Fonts\segoeuib.ttf")   # Segoe UI Bold (ships with Windows); set STEVE_FONT to use another Arabic-capable bold font
RESH = arabic_reshaper.ArabicReshaper(configuration={"support_ligatures": True})


def ar(t):
    return get_display(RESH.reshape(t))


def block_face(base, lines, out, size=64, fs=26):
    """lines: list of text lines, stacked and centred."""
    im = Image.open(os.path.join(TEX, base + ".png")).convert("RGBA").resize((size, size), Image.NEAREST)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"                                  # no smoothing: pixel look
    shadow = (40, 10, 10, 255) if base.startswith("red") else (8, 50, 20, 255)
    while True:
        f = ImageFont.truetype(FONT, fs)
        bbs = [d.textbbox((0, 0), ar(t), font=f) for t in lines]
        if max(b[2] - b[0] for b in bbs) <= size - 8 or fs <= 10:
            break
        fs -= 1
    lh = max(b[3] - b[1] for b in bbs) + 4
    y0 = (size - lh * len(lines)) / 2
    for i, (t, bb) in enumerate(zip(lines, bbs)):
        x = (size - (bb[2] - bb[0])) / 2 - bb[0]
        y = y0 + i * lh + (lh - (bb[3] - bb[1])) / 2 - bb[1]
        d.text((x + 2, y + 2), ar(t), font=f, fill=shadow)
        d.text((x, y), ar(t), font=f, fill=(255, 255, 255, 255))
    im.save(os.path.join(TEX, out))


def nametag(txt, out, fs=96, fill=(255, 255, 255), shade=(60, 60, 60)):
    """fill/shade: text colour and its shadow (the game's gold text is FFAA00 with a shadow at a quarter: 3F2A00)."""
    f = ImageFont.truetype(FONT, fs)
    t = ar(txt)
    bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), t, font=f)
    w, h = bb[2] - bb[0] + 40, 110
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), fill=(24, 24, 24, 255))          # solid dark plate (see-through would blend with the key colour)
    ty = (h - (bb[3] - bb[1])) / 2 - bb[1]
    d.text((20 - bb[0] + 5, ty + 5), t, font=f, fill=shade + (255,))   # soft shadow
    d.text((20 - bb[0], ty), t, font=f, fill=fill + (255,))
    im.save(os.path.join(TEX, out))
    return im.size


def grain(base, cells, seed, cell=1):
    """Minecraft-style texel grain: most texels are exactly `base`, some a bit darker (like concrete / wool).
    The red bar keeps R=255 on ~80% of texels, so its flat area still reads as FF0000; the mean R is a little lower (said in PROGRESS)."""
    import random
    rnd = random.Random(seed)
    w, h = cells
    im = Image.new("RGBA", (w * cell, h * cell), base + (255,))
    d = ImageDraw.Draw(im)
    for j in range(h):
        for i in range(w):
            r = rnd.random()
            k = 0.88 if r < 0.12 else (0.78 if r < 0.18 else 1.0)
            if k < 1.0:
                c = tuple(int(v * k) for v in base) + (255,)
                d.rectangle((i * cell, j * cell, i * cell + cell - 1, j * cell + cell - 1), fill=c)
    return im


OUTL = 2          # text outline width in texture pixels (the bar face is 192 x 64)


def bar_face(base, shade, text, out, w=192, h=64, fs=40, text_out=None):
    """Wide 3:1 pixel bar face with 4 px texel grain. A 3 px darker rim gives the pixel-block look."""
    im = grain(base, (w // 4, h // 4), seed=len(out), cell=4)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, h - 1), outline=shade + (255,), width=3)
    for x, y in ((3, 3), (w - 4, 3), (3, h - 4), (w - 4, h - 4)):
        im.putpixel((x, y), shade + (255,))                     # stepped inner corners
    d.fontmode = "1"
    t = ar(text)
    while text:
        f = ImageFont.truetype(FONT, fs)
        bb = d.textbbox((0, 0), t, font=f, stroke_width=OUTL)
        if bb[2] - bb[0] <= w - 28 and bb[3] - bb[1] <= h - 20:
            break
        fs -= 1
    if text:
        x = (w - (bb[2] - bb[0])) / 2 - bb[0]
        y = (h - (bb[3] - bb[1])) / 2 - bb[1]
        dark = tuple(c // 4 for c in shade) + (255,)          # thick dark outline: the words read on busy footage
        d.text((x + 2, y + 2), t, font=f, fill=dark, stroke_width=OUTL, stroke_fill=dark)
        d.text((x, y), t, font=f, fill=(255, 255, 255, 255), stroke_width=OUTL, stroke_fill=dark)
        if text_out:                                   # the same text alone, see-through elsewhere: drawn over the cracks
            ti = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            td = ImageDraw.Draw(ti)
            td.fontmode = "1"
            td.text((x + 2, y + 2), t, font=f, fill=dark, stroke_width=OUTL, stroke_fill=dark)
            td.text((x, y), t, font=f, fill=(255, 255, 255, 255), stroke_width=OUTL, stroke_fill=dark)
            ti.save(os.path.join(TEX, text_out))
    im.save(os.path.join(TEX, out))


if __name__ == "__main__":
    bar_face((255, 0, 0), (110, 0, 0), "اشتراك", "bar_red.png", text_out="bar_red_text.png")
    bar_face((255, 0, 0), (110, 0, 0), "", "bar_red_plain.png")                       # the dropped mini bar: no tiny unreadable text
    for name, rgb, cells in (("red_side", (170, 0, 0), (10, 16)), ("red_top", (215, 20, 20), (48, 10)),
                             ("grn_side", (18, 160, 40), (10, 16)), ("grn_top", (70, 240, 95), (48, 10))):
        grain(rgb, cells, seed=len(name) * 7).save(os.path.join(TEX, name + ".png"))
    bar_face((30, 226, 60), (8, 105, 28), "تم الاشتراك", "bar_green.png", fs=36)
    print(nametag("نوب", "tag_noob.png"), nametag("اسطورة", "tag_legend.png"),
          nametag("اسطورة", "tag_legend_gold.png", fill=(255, 170, 0), shade=(63, 42, 0)))   # the rank-up tag: the game's gold text
