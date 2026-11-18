"""Copy the Minecraft textures this animation uses from your own game install into steve/tex (read-only on the game files).
The textures belong to Mojang and are not stored in this repository. Run once: python fetch_assets.py
Needs Minecraft Java 1.21.1 launched once, so the jar exists. Set MC_DIR to use another .minecraft folder."""
import io
import os
import zipfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tex")
MC = os.environ.get("MC_DIR", os.path.expandvars(r"%APPDATA%\.minecraft"))
JAR = os.path.join(MC, "versions", "1.21.1", "1.21.1.jar")
BASE = "assets/minecraft/textures/"

# file in tex/  <-  path inside the jar, copied as is
COPY = {
    "steve.png": "entity/player/wide/steve.png",
    "netherite_pickaxe.png": "item/netherite_pickaxe.png",
    "enchanted_glint_item.png": "misc/enchanted_glint_item.png",
    "experience_orb.png": "entity/experience_orb.png",
}
# crack_N.png is the game's destroy_stage_N as a see-through overlay: dark texels -> black 190, light texels -> a faint 30
# (the light texels are black in stages 0, 1, 3 and white in the others, as used in the final render)
BLACK_LIGHT = {0, 1, 3}

os.makedirs(OUT, exist_ok=True)
with zipfile.ZipFile(JAR) as z:
    for name, src in COPY.items():
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(z.read(BASE + src))
        print("copied", name)
    for n in range(10):
        d = Image.open(io.BytesIO(z.read(BASE + "block/destroy_stage_%d.png" % n))).convert("RGBA")
        o = Image.new("RGBA", d.size)
        px, qx = o.load(), d.load()
        for y in range(d.size[1]):
            for x in range(d.size[0]):
                r, _, _, a = qx[x, y]
                if a <= 1:
                    continue
                if r == 61:
                    px[x, y] = (0, 0, 0, 190)
                else:
                    c = 0 if n in BLACK_LIGHT else 255
                    px[x, y] = (c, c, c, 30)
        o.save(os.path.join(OUT, "crack_%d.png" % n))
        print("made crack_%d.png" % n)
