"""Copy real Minecraft 1.21 sounds from the local game assets to wav files in steve/sound (read-only on the game files)."""
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sound")
os.makedirs(OUT, exist_ok=True)
ap = os.path.expandvars(r"%APPDATA%\.minecraft\assets")
objs = json.load(open(os.path.join(ap, "indexes", "1.21.json")))["objects"]
want = {
    "hit_stone1": "dig/stone1", "hit_stone2": "dig/stone2",
    "break_pop": "random/pop", "reveal_orb": "random/orb",
    # redstone block = the game's METAL sound type: its hit sound is step/stone1-6 (played at pitch 0.75), its break is dig/stone at 1.2
    "metal_hit1": "step/stone1", "metal_hit2": "step/stone2", "metal_hit3": "step/stone3",
    "metal_hit4": "step/stone4", "metal_hit5": "step/stone5", "metal_hit6": "step/stone6",
    "step_grass1": "step/grass1", "step_grass2": "step/grass2", "step_grass3": "step/grass3", "step_grass4": "step/grass4",
}
for name, key in want.items():
    h = objs["minecraft/sounds/%s.ogg" % key]["hash"]
    src = os.path.join(ap, "objects", h[:2], h)
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "ogg", "-i", src, "-ar", "48000", "-ac", "2",
                        os.path.join(OUT, name + ".wav")], capture_output=True, text=True)
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                        os.path.join(OUT, name + ".wav")], capture_output=True, text=True).stdout.strip()
    print(name, r.returncode, d, r.stderr[:80])
