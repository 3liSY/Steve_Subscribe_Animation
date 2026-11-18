"""make_video.py <frames_dir> <out.mp4> [fps_in=30] [key=FF00B3]
Puts the see-through PNG frames on the key colour, mixes the real game sounds at the picture's event times, writes H.264 + AAC.
Event times come from <frames_dir>/events.json, written by steve_scene.py (video seconds, frame 0 = 0, impact freeze included).
The video size is the frames' own size (long 16:9 or Shorts 9:16). Sounds start on the contact frame.
Sound set (round 2): the bar is a redstone block, so the hits use the game's METAL sounds (step/stone at pitch 0.75, the game's
hit pitch for metal), the break adds the game's metal break (dig/stone at pitch 1.2), then the pop, the small orb sound on the
green snap, a few quiet orb pickups and grass footsteps. No big achievement sound."""
import json
import os
import random
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
frames, out = sys.argv[1], sys.argv[2]
fps_in = int(sys.argv[3]) if len(sys.argv) > 3 else 30
key = sys.argv[4] if len(sys.argv) > 4 else "FF00B3"
S = os.path.join(HERE, "sound")
pngs = sorted(f for f in os.listdir(frames) if f.startswith("f") and f.endswith(".png"))
w, h = Image.open(os.path.join(frames, pngs[0])).size
ev = json.load(open(os.path.join(frames, "events.json")))
random.seed(5)

HIT_VARY = [(0.85, 0.75), (0.72, 0.70), (0.80, 0.79), (0.70, 0.73)]   # (volume, pitch): the game's metal hit pitch 0.75 with a little spread
events = [(S + "/metal_hit%d.wav" % (i % 6 + 1), t, HIT_VARY[i % 4][0], HIT_VARY[i % 4][1]) for i, t in enumerate(ev["hits"])]
tb = ev["break"]
events += [(S + "/metal_hit5.wav", tb, 1.0, 0.72),          # the last strike: the metal hit ...
           (S + "/hit_stone2.wav", tb, 1.4, 1.2),           # ... plus the game's metal break (dig/stone at 1.2), louder
           (S + "/break_pop.wav", ev["burst"], 0.75, 1.0),  # the pop as the pieces burst out
           (S + "/reveal_orb.wav", ev["burst"] + 0.02, 1.5, 1.0)]   # the small orb sound as the green bar snaps in
orbs = ev["orbs"]
for t in (orbs[0], orbs[len(orbs) // 2], orbs[-1]):           # 3 quiet pickups as the orbs reach Steve (game: random pitch)
    events.append((S + "/reveal_orb.wav", t, 0.35, random.uniform(0.9, 1.3)))
events += [(S + "/step_grass%d.wav" % (i % 4 + 1), t, 0.8, 1.0) for i, t in enumerate(ev["steps"])]
events.append((S + "/reveal_orb.wav", ev["tag"], 0.9, 1.5))      # the rank-up gets its own small high ding (not the level-up sound)
events += [(S + "/step_grass%d.wav" % (i % 4 + 1), t, 0.7, 0.9) for i, t in enumerate(ev.get("lands", []))]   # hop landings
if "bar_in" in ev:
    events.append((S + "/hit_stone1.wav", ev["bar_in"] + 0.02, 0.45, 0.8))   # the game's block place, quiet, as the bar pops in
for i, t in enumerate(ev.get("taps", [])):                   # pointing round: proud taps on the green bar, light metal tick + sparkle
    events += [(S + "/metal_hit%d.wav" % (i % 6 + 2), t, 0.40, 0.95), (S + "/reveal_orb.wav", t + 0.02, 0.30, 1.9)]
if "bar_out" in ev:
    events.append((S + "/break_pop.wav", ev["bar_out"], 0.55, 1.3))   # a small pop as everything vanishes (time already on the swell peak)
total = len(pngs) / float(fps_in)                              # the sound ends with the picture
events = [e for e in events if e[1] < total - 0.05]

# frame list for the concat reader (frames may be every 2nd number), kept in the frames folder (scratch)
lst = os.path.join(frames, "frames.txt")
with open(lst, "w") as fh:
    for p in pngs:
        fh.write("file '%s'\nduration %.6f\n" % (os.path.join(frames, p).replace("\\", "/"), 1.0 / fps_in))
    fh.write("file '%s'\n" % os.path.join(frames, pngs[-1]).replace("\\", "/"))
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst]
for wav, _, _, _ in events:
    cmd += ["-i", wav]
fc = ["color=c=0x%s:s=%dx%d:r=%d[bg]" % (key, w, h, fps_in)]
parts = []
for i, (_, t, g, p) in enumerate(events):
    ms = int(round(t * 1000))
    fc.append("[%d:a]aresample=48000,asetrate=%d,aresample=48000,adelay=%d|%d,volume=%.2f[a%d]" % (i + 1, int(48000 * p), ms, ms, g, i))
    parts.append("[a%d]" % i)
fc.append("".join(parts) + "amix=inputs=%d:normalize=0,alimiter=limit=0.8:level=0,apad=whole_dur=%.3f[aout]" % (len(events), total))
fc.append("[0:v]fps=%d[fg];[bg][fg]overlay=shortest=1,format=yuv420p[v]" % fps_in)
cmd += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[aout]", "-t", "%.3f" % total, "-c:v", "libx264", "-crf", "18",
        "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
print(subprocess.run(cmd, capture_output=True, text=True).stderr[-600:] or "ok", len(events), "sounds", "%dx%d" % (w, h), "%.2fs" % total)
