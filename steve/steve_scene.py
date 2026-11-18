"""steve_scene.py - Steve mines the "subscribe" block with a netherite pickaxe, it breaks, a green "subscribed" block pops in.
Blender 5.2 EEVEE, see-through frames (composited on a key colour afterwards). Everything is set by code per frame, no keyframes.
The player rig (skin, limbs, bendable joints) comes from rig/steve_rig.py.

  blender -b -P steve_scene.py -- <outdir> [res=960] [samples=16] [step=2] [frames=0-320] [still=190]

Units: 1 block = 1 unit, Steve 2 units tall. Block at x 0..1, y 0..1, z 0..1. Camera sees Steve's right side/front, Steve walks in from +x facing -x.
"""
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Vector, Euler, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
TEXD = os.path.join(HERE, "tex")
SCENE = os.path.join(HERE, "rig")            # the player rig code
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUTDIR = args[0]
OPT = dict(a.split("=", 1) for a in args[1:] if "=" in a)
F = lambda k, d: float(OPT.get(k, d))  # noqa: E731
os.environ["VOX3D"] = "0"
os.environ["JOINTOV"] = "auto"

_thumb = open(os.path.join(SCENE, "steve_rig.py"), encoding="utf-8").read().split('\nT121 = os.path.join(D, "tex121")')[0]
_thumb = _thumb.replace("D = os.path.dirname(os.path.abspath(__file__))", "D = SCENE").replace(
    'OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.join(D, "thumb.png")', "OUT = ''")
ARMW = 4                                                    # Steve (wide) has 4 px arms
_thumb = _thumb.replace('limb("arm" + side, (3, 12, 4), uv', 'limb("arm" + side, (ARMW, 12, 4), uv').replace(
    '(("R", (40, 16), (40, 32), -5.5), ("L", (32, 48), (48, 48), 5.5))', '(("R", (40, 16), (40, 32), -(4 + ARMW / 2)), ("L", (32, 48), (48, 48), 4 + ARMW / 2))')
exec(compile(_thumb, "steve_rig.py", "exec"), globals())        # skin_mat, player, block_mat, rot, upd, snap_feet, DIRS, sc, PX

FPS = 60
# ------------------------------------------------------------------ timeline (seconds)
# Round 2 (2026-11-18): two versions from one scene. ver=long (16:9) or ver=shorts (9:16). Times are VIDEO seconds (see NOTES.md table).
VER = OPT.get("ver", "long")
LONG = VER != "shorts"
BW, BH, BD = 2.4, 0.8, 0.5          # the bar: 3:1 wide, x 0..BW, sits on the ground
STEVE_Y = 0.5 - (4 + ARMW / 2) * PX     # Steve stands so his RIGHT (pickaxe) arm is over the bar's middle depth, not behind it
SX = BW + F("sxo", 0.55)           # Steve's standing x: the pick head lands on the bar top about 0.2 inside its right end
START = 0.25                       # video frame 0 = scene time START
FRZ = 2 / 30.0                     # impact freeze on the break: 2 frames at 30 fps (everything holds, only the camera shakes)
V = lambda v: START + v            # noqa: E731  video time before the break -> scene time
A = lambda v: START + v - FRZ      # noqa: E731  video time after the break -> scene (animation) time
SLOW = F("slow", 1.15)             # pointing round (2026-11-18): 3li found the cut a little fast; the whole thing plays 15% slower
HOP_H = F("hop", 0.34)           # hop height (game jump is 1.25 blocks; lower so the tag stays in frame)
HOP_S = F("hops", 0.22)          # the two little hops while pointing
if LONG:
    X0, T_ARR = SX + 1.7, V(0.52)                     # walks in 0.00-0.52 (enters at full speed, eases to a stop)
    HITS = [V(0.70), V(1.00), V(1.30)]                 # 3 hits, the last one breaks (0.30 s per swing, like the game's 6 ticks)
    JUMPS = [(A(1.58), 0.55, HOP_H)]                   # (take-off, air time, height): one happy hop while the orbs fly in
else:
    X0, T_ARR = SX + 0.45, V(0.20)                    # already at the bar: one short step in
    HITS = [V(0.50), V(0.80)]                          # 2 hits, the last one breaks; the clean red word shows 15 frames first
    JUMPS = [(A(1.05), 0.45, HOP_H)]
# pointing round: after the hop lands, the green bar stays and Steve keeps pointing at it with his free (left) hand.
# Beats (scene s after P0): look at the bar, 3 quick sneaks, 2 pickaxe taps on the bar, 2 little hops, a double-take and nods.
P0 = JUMPS[0][0] + JUMPS[0][1]                         # the hop landing
PD = F("pointlen", 3.04)                               # pointing time (3.5 s of video at SLOW 1.15; 3li: "about 3-4")
CR_DN, CR_UP = F("crdn", 0.075), F("crup", 0.065)      # one spam press: held down, then up (scene s; ~6 a second, like a real tap-spam)
CROUCH = [P0 + 0.30 + i * (CR_DN + CR_UP) for i in range(5)]          # burst 1: 5 fast sneaks at the viewer
CROUCH += [P0 + 2.60 + i * (CR_DN + CR_UP) for i in range(3)]        # burst 2: after the double-take, sneak-spam while pointing
TAPS = [P0 + 1.05, P0 + 1.35]                          # proud pickaxe taps on the green bar
JUMPS += [(P0 + 1.62, 0.36, HOP_S), (P0 + 2.02, 0.36, HOP_S)]
JABS = [P0 + 1.80, P0 + 2.20, P0 + 2.52, P0 + 2.70, P0 + 2.88]     # point pumps: hop tops, then three to end
TP = P0 + PD                                           # quick pop-out: Steve, tag and bar swell a little, then vanish
POP = 0.26
T_END = TP + POP
T_BREAK = HITS[-1]                 # contact of the last hit; the freeze holds here, the bar bursts FRZ later (video)
SNAP = 4 / 30.0                    # green bar: in at the burst, overshoots, settles in 4 frames at 30 fps
T_TAG = T_BREAK + 0.133            # noob -> legend tag pop (video 1.30 long / 0.70 shorts)
ARM_REST = -18.0                   # the game's "holding an item" arm: raised 18 deg forward (HumanoidModel ArmPose.ITEM, -PI/10)
ARM_HIT, ARM_UP = F("ahit", -21.0), F("aup", -112.0)   # right arm pitch at the hit / top of the swing (deg, negative = forward/up)
ARM_PULL = ARM_UP - 18.0
ARM_READY = F("aready", -27.0)     # after the break: held a little higher than rest, so the pick head stays above the green bar           # the last swing pulls back further and holds 3 frames (anticipation)


def ss(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, u):
    return a + (b - a) * u


# ------------------------------------------------------------------ rig
steve = player("S", os.path.join(TEXD, "steve.png"), {})
for o in steve["meshes"]:
    o.hide_render = False
snap_feet(steve, ["legR", "legL"])
BASEZ = steve["base"].location.z


def grip_item():
    img = bpy.data.images.load(os.path.join(TEXD, "netherite_pickaxe.png"), check_existing=True)
    w, h = img.size
    px = list(img.pixels)
    solid = {(i, j) for j in range(h) for i in range(w) if px[((h - 1 - j) * w + i) * 4 + 3] > 0.5}
    me = bpy.data.meshes.new("pick")
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    gx, gy = 2.0, 13.5                                        # the grip pixel (handle, lower left)
    for (i, j) in solid:
        cy, cz = -(i + 0.5 - gx) * PX, -(j + 0.5 - gy) * PX
        u, v = (i + 0.5) / w, 1 - (j + 0.5) / h
        for n, quad in DIRS.items():
            if n[0] == 0 and (i - n[1], j - n[2]) in solid:
                continue
            vs = [bm.verts.new(((a_ - 0.5) * PX, cy + (b_ - 0.5) * PX, cz + (c_ - 0.5) * PX)) for a_, b_, c_ in quad]
            f = bm.faces.new(vs)
            for lp in f.loops:
                lp[uvl].uv = (u, v)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("pick", me)
    sc.collection.objects.link(o)
    o.data.materials.append(block_mat("pickm", "netherite_pickaxe", texdir=TEXD, rough=0.45))
    return o


# The game's own third-person right-hand hold (Minecraft 1.21.1, read-only from the jar, worked out in C:/Temp/sub_capture/hold_math.py):
# ItemInHandLayer turns the item -90 X, 180 Y, moves it (1, 2, -10) px, then handheld.json thirdperson_righthand: rotation [0,-90,55],
# translation [0,4,0.5], scale 0.85. Result in the arm's frame (arm hanging): the grip pixel sits 8 px below the shoulder pivot
# (2 px above the arm's end, inside the arm), 0.75 px behind the arm's centre; the shaft sticks straight forward, 13 deg down;
# the head stands upright at the front. Texture (right, down) -> (forward, down) = 0.85 * [[0.819, -0.573], [-0.573, -0.820]]
# (a mirror: we see the item's back face). There is no wrist and no elbow bend in the game: the item is fixed to the arm.
hand = empty("hand", steve["elbowR"], (0, 0.75, -4.0))       # the grip point: shoulder pivot - 8 px (the elbow sits at pivot - 4 px)
pick = grip_item()
pick.parent = hand
ISC = F("isc", 0.85)
pick.matrix_basis = Matrix.Rotation(math.radians(-35.0), 4, "X") @ Matrix.Diagonal((-ISC, ISC, -ISC, 1.0))


def add_glint(m):
    """The game's enchant glint: its own purple texture (misc/enchanted_glint_item.png), added on top, tilted 10 deg, sliding slowly.
    Low strength, on the item's own pixels only: no halo, no glow outside the pickaxe."""
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    surf = out.inputs["Surface"].links[0].from_socket
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Rotation"].default_value = (math.radians(10), 0, 0)
    mp.inputs["Scale"].default_value = (1.0, 0.45, 0.45)
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(os.path.join(TEXD, "enchanted_glint_item.png"), check_existing=True)
    tx.extension = "REPEAT"
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = F("glint", 0.45)
    ad = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    # the texture is 2D: use the item's own plane (object y, z) as its u, v
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    com = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(mp.outputs["Vector"], sep.inputs[0])
    nt.links.new(sep.outputs["Y"], com.inputs["X"])
    nt.links.new(sep.outputs["Z"], com.inputs["Y"])
    nt.links.new(com.outputs[0], tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], em.inputs["Color"])
    nt.links.new(surf, ad.inputs[0])
    nt.links.new(em.outputs["Emission"], ad.inputs[1])
    nt.links.new(ad.outputs["Shader"], out.inputs["Surface"])
    return mp


GLINT = add_glint(pick.data.materials[0])

# ------------------------------------------------------------------ blocks
def cube_obj(name, mats, size=(1.0, 1.0, 1.0), repeat_u=1.0):
    """mats: [front(-y), sides, top]. size: (x, y, z)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    for n, quad in DIRS.items():
        vs = [bm.verts.new(((a - 0.5) * size[0], (b - 0.5) * size[1], (c - 0.5) * size[2])) for a, b, c in quad]
        f = bm.faces.new(vs)
        f.material_index = 0 if n == (0, -1, 0) else (2 if n == (0, 0, 1) else 1)
        for lp, uv in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            lp[uvl].uv = uv
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    for m in mats:
        o.data.materials.append(m)
    return o


def flat_mat(name, rgb=None, png=None):
    """Unlit colour: the pixels come out exactly as the texture / colour (no light shifts them)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    if png:
        tx = nt.nodes.new("ShaderNodeTexImage")
        tx.image = bpy.data.images.load(os.path.join(TEXD, png), check_existing=True)
        tx.interpolation = "Closest"
        nt.links.new(tx.outputs["Color"], em.inputs["Color"])
    else:
        lin = [(c / 255.0) ** 2.2 if c < 255 else 1.0 for c in rgb]
        em.inputs["Color"].default_value = (lin[0], lin[1], lin[2], 1)
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return m


RED_SIDE, RED_TOP, GRN_SIDE, GRN_TOP = (170, 0, 0), (215, 20, 20), (18, 160, 40), (70, 240, 95)
mat_front_r = flat_mat("barR", png="bar_red.png")
mat_front_g = flat_mat("barG", png="bar_green.png")
mat_rs, mat_rt = flat_mat("rs", png="red_side.png"), flat_mat("rt", png="red_top.png")      # texel grain like a real block
mat_gs, mat_gt = flat_mat("gs", png="grn_side.png"), flat_mat("gt", png="grn_top.png")
mat_drop = flat_mat("dropF", png="bar_red_plain.png")
BLK = cube_obj("blk", [mat_front_r, mat_rs, mat_rt], (BW, BD, BH))
GRN = cube_obj("grn", [mat_front_g, mat_gs, mat_gt], (BW, BD, BH))
DROP = cube_obj("drop", [mat_drop, mat_rs, mat_rt], (BW * 0.3, BD * 0.3, BH * 0.3))          # the dropped item: no tiny unreadable text
BAR_C = Vector((BW / 2, 0.5, BH / 2))


def pixel_shadow(name, rx, ry, cell=1 / 16.0, rect=False):
    """Flat blocky shadow on the ground: rows of whole texel cells, solid dark grey (no see-through edge)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    n = int(round(ry / cell))
    for j in range(-n, n):
        yc = (j + 0.5) * cell
        hw = rx if rect else rx * math.sqrt(max(0.0, 1 - (yc / ry) ** 2))
        k = int(round(hw / cell))
        if k < 1:
            continue
        vs = [bm.verts.new(c) for c in ((-k * cell, j * cell, 0), (k * cell, j * cell, 0), (k * cell, (j + 1) * cell, 0), (-k * cell, (j + 1) * cell, 0))]
        bm.faces.new(vs)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    o.data.materials.append(SH_MAT)
    return o


SH_MAT = flat_mat("shadow", rgb=(38, 38, 42))
SH_STEVE = pixel_shadow("shSteve", 0.42, 0.26)
SH_BAR = pixel_shadow("shBar", BW / 2 + 0.12, BD / 2 + 0.12, rect=True)
SH_BAR.location = (BW / 2 + 0.06, 0.5, 0.003)
def crack_mat(n):
    """Dark crack lines from the game's destroy_stage texture alpha, unlit, so the red under them stays red."""
    m = bpy.data.materials.new("crack%d" % n)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.004, 0.0, 0.0, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(os.path.join(TEXD, "crack_%d.png" % n), check_existing=True)
    tx.interpolation = "Closest"
    boost = nt.nodes.new("ShaderNodeMath")
    boost.operation = "MULTIPLY"
    boost.use_clamp = True
    boost.inputs[1].default_value = F("crackk", 2.2)
    nt.links.new(tx.outputs["Alpha"], boost.inputs[0])
    nt.links.new(boost.outputs[0], mx.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mx.inputs[1])
    nt.links.new(em.outputs["Emission"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    m.surface_render_method = "BLENDED"
    return m


crack_mats = {n: crack_mat(n) for n in range(10)}     # all 10 game stages (destroy_stage_0..9)


def crack_tile(k):
    """One BH x BH square crack overlay on the bar's front; tiles 1 is mirrored so the three do not look identical."""
    me = bpy.data.meshes.new("crk%d" % k)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    x0 = k * BH - BW / 2
    vs = [bm.verts.new(c) for c in ((x0, -BD / 2 - 0.004, -BH / 2), (x0 + BH, -BD / 2 - 0.004, -BH / 2),
                                   (x0 + BH, -BD / 2 - 0.004, BH / 2), (x0, -BD / 2 - 0.004, BH / 2))]
    f = bm.faces.new(vs)
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)] if k != 1 else [(1, 0), (0, 0), (0, 1), (1, 1)]
    for lp, uv in zip(f.loops, uvs):
        lp[uvl].uv = uv
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("crk%d" % k, me)
    sc.collection.objects.link(o)
    o.data.materials.append(crack_mats[0])
    try:
        o.visible_shadow = False
    except Exception:
        pass
    return o


CRKS = [crack_tile(k) for k in range(3)]


def text_over():
    """The red bar's text alone, just in front of the cracks, so the cracks never cover the word."""
    m = bpy.data.materials.new("barText")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(os.path.join(TEXD, "bar_red_text.png"), check_existing=True)
    tx.interpolation = "Closest"
    nt.links.new(tx.outputs["Color"], em.inputs["Color"])
    nt.links.new(tx.outputs["Alpha"], mx.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mx.inputs[1])
    nt.links.new(em.outputs["Emission"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    m.surface_render_method = "DITHERED"             # alpha is 0 or 1 only, so this is a clean cut-out
    me = bpy.data.meshes.new("barText")
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    yv = -BD / 2 - 0.006
    vs = [bm.verts.new(c) for c in ((-BW / 2, yv, -BH / 2), (BW / 2, yv, -BH / 2), (BW / 2, yv, BH / 2), (-BW / 2, yv, BH / 2))]
    f = bm.faces.new(vs)
    for lp, uv in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        lp[uvl].uv = uv
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("barText", me)
    sc.collection.objects.link(o)
    o.data.materials.append(m)
    try:
        o.visible_shadow = False
    except Exception:
        pass
    return o


TXT = text_over()

# debris: pieces on a shared mesh; each has a start time, start pos, velocity, life, size
random.seed(7)


def chunk_mesh(k, big):
    """A debris cube whose every face shows one small patch of the bar's own face texture (like the game's block-break particles)."""
    uw, vh = (20 / 192, 20 / 64) if big else (8 / 192, 8 / 64)
    lo = random.choice((0.02, 0.84))                     # sample the text-free ends only, so chunks are red texels, not white letter bits
    u0, v0 = random.uniform(lo, lo + 0.14 - uw), random.uniform(0.05, 0.95 - vh)
    o = cube_obj("chunk%d" % k, [mat_front_r, mat_front_r, mat_front_r], (1.0, 1.0, 1.0))
    uvl = o.data.uv_layers.active.data
    for lp in uvl:
        lp.uv = (u0 + lp.uv[0] * uw, v0 + lp.uv[1] * vh)
    me = o.data
    bpy.data.objects.remove(o)
    return me


SMALL = [chunk_mesh(k, False) for k in range(8)]
BIG = [chunk_mesh(8 + k, True) for k in range(6)]
PIECES = []


def add_piece(t0, p, v, life, size):
    o = bpy.data.objects.new("piece", random.choice(BIG if size > 0.15 else SMALL))
    sc.collection.objects.link(o)
    PIECES.append(dict(o=o, t0=t0, p=Vector(p), v=Vector(v), life=life, size=size, spin=Vector((random.uniform(-9, 9) for _ in range(3)))))


for i, tc in enumerate(HITS[:-1]):                       # chips on every hit, from the struck spot on the bar's top
    for _ in range(12):
        add_piece(tc, (BW - 0.25 + random.uniform(-0.08, 0.08), random.uniform(0.3, 0.6), BH - 0.03),
                  (random.uniform(0.6, 2.2), random.uniform(-1.4, 0.4), random.uniform(1.0, 2.8)), random.uniform(0.35, 0.6), random.uniform(0.07, 0.12))
for i in range(84):                                      # the break: the bar's whole volume bursts; a few big chunks show the bar's face
    # pieces burst up and out of the TOP and the ends, drifting back, so none crosses the green bar's text face
    # round 3: start at the top edge and fly up faster, so no red piece still sits on the green bar 2 frames after the burst
    p = (random.uniform(0.1, BW - 0.1), random.uniform(0.3, 0.7), random.uniform(BH * 0.8, BH + 0.04))
    d = Vector((p[0] - BW / 2, p[1] - 0.5, p[2] - BH / 2))
    big = i < 6
    add_piece(T_BREAK, p, (d.x * 2.0 + random.uniform(-0.5, 1.0), abs(d.y) * 2 + random.uniform(0.5, 1.2), d.z * 3 + random.uniform(2.6, 4.2) * (0.8 if big else 1.0)),
              random.uniform(0.24, 0.30) if big else random.uniform(0.20, 0.30), random.uniform(0.15, 0.20) if big else random.uniform(0.075, 0.12))

def star_obj(name, rgb, rs):
    """Flat billboard star burst (XZ plane), triangle fan: radii per point, round 3 extras (replaces the white box flash)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    c = bm.verts.new((0, 0, 0))
    n = len(rs)
    ring = []
    for k in range(2 * n):
        r = rs[k // 2] if k % 2 == 0 else 0.16
        ang = math.pi * k / n
        ring.append(bm.verts.new((r * math.cos(ang), 0, r * math.sin(ang))))
    for k in range(2 * n):
        bm.faces.new((c, ring[k], ring[(k + 1) % (2 * n)]))
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    o.data.materials.append(flat_mat(name, rgb=rgb))
    o.visible_shadow = False
    return o


FLASH = star_obj("flash", (255, 255, 255), [1.0, 0.55, 0.8, 0.5, 1.0, 0.55, 0.8, 0.5])      # 8 points, long ones left/right
FLASH_IN = star_obj("flash_in", (255, 236, 140), [0.55, 0.3, 0.45, 0.3, 0.55, 0.3, 0.45, 0.3])  # warm core in front


def spark_obj(k):
    """A small square pixel spark (billboard), Minecraft gold."""
    me = bpy.data.meshes.new("spark%d" % k)
    bm = bmesh.new()
    hh = 0.5
    bm.faces.new([bm.verts.new(c) for c in ((-hh, 0, -hh), (hh, 0, -hh), (hh, 0, hh), (-hh, 0, hh))])
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("spark%d" % k, me)
    sc.collection.objects.link(o)
    o.data.materials.append(flat_mat("spark%d" % k, rgb=(255, 214, 40) if k % 2 else (255, 255, 160)))
    o.visible_shadow = False
    return o


SPARKS = []
for k in range(10):
    ang = 2 * math.pi * k / 10 + random.uniform(-0.2, 0.2)
    SPARKS.append(dict(o=spark_obj(k), d=Vector((math.cos(ang), 0, math.sin(ang) * 0.75)), sp=random.uniform(1.4, 2.2), size=random.uniform(0.075, 0.12)))


def happy_obj(k):
    """A small green pixel sparkle (like the game's happy-villager particle), billboard, unlit."""
    me = bpy.data.meshes.new("happy%d" % k)
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(c) for c in ((-0.5, 0, -0.5), (0.5, 0, -0.5), (0.5, 0, 0.5), (-0.5, 0, 0.5))])
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("happy%d" % k, me)
    sc.collection.objects.link(o)
    o.data.materials.append(flat_mat("happy%d" % k, rgb=(60, 230, 90) if k % 2 else (190, 255, 170)))
    o.visible_shadow = False
    return o


HAPPY = []                                               # pointing round: 7 sparkles fly up from the struck spot on each tap
for i, tc in enumerate(TAPS):
    for k in range(7):
        ang = math.radians(25 + 130 * k / 6.0 + random.uniform(-8, 8))
        HAPPY.append(dict(o=happy_obj(7 * i + k), t0=tc, d=Vector((math.cos(ang), 0, math.sin(ang))),
                          sp=random.uniform(1.1, 1.8), size=random.uniform(0.06, 0.10)))


# ------------------------------------------------------------------ name tags (billboards, unlit, follow Steve's head)
def tag_obj(name, png):
    img = bpy.data.images.load(os.path.join(TEXD, png), check_existing=True)
    w, h = img.size
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    hh = 0.30 * F("tagk", 1.3)
    ww = hh * w / h
    vs = [bm.verts.new(c) for c in ((-ww / 2, 0, -hh / 2), (ww / 2, 0, -hh / 2), (ww / 2, 0, hh / 2), (-ww / 2, 0, hh / 2))]
    f = bm.faces.new(vs)
    for lp, uv in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        lp[uvl].uv = uv
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = img
    tx.interpolation = "Linear"
    nt.links.new(tx.outputs["Color"], em.inputs["Color"])
    nt.links.new(tx.outputs["Alpha"], mx.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mx.inputs[1])
    nt.links.new(em.outputs["Emission"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    m.surface_render_method = "BLENDED"
    o.data.materials.append(m)
    o.visible_shadow = False
    o["em"] = em.name
    return o


TAG_N = tag_obj("tagN", "tag_noob.png")
TAG_L = tag_obj("tagL", "tag_legend_gold.png")
TAG_L_EM = TAG_L.data.materials[0].node_tree.nodes[TAG_L["em"]].inputs["Strength"]

# ------------------------------------------------------------------ camera, light, render
cam_d = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
if LONG:
    cam_d.lens = F("lens", 36)
    CAM0 = Vector((F("cx", -0.4), F("cy", -5.6), F("cz", 1.55)))
    LOOK = Vector((F("lx", 1.68), F("ly", 0.5), F("lz", 1.25)))
    cam_d.shift_x, cam_d.shift_y = F("shx", 0.0), F("shy", 0.0)
else:                                    # Shorts 9:16: the width is fitted; the action sits a bit above the middle,
    cam_d.sensor_fit = "HORIZONTAL"      # clear of the right-side buttons and the bottom caption area
    cam_d.sensor_width = 36
    cam_d.lens = F("lens", 48.5)         # round 3 extras: 3li picked old size + lower; 48.5 (not 50) keeps the bar (break shake) and gold tag (pop) inside the side edges
    CAM0 = Vector((F("cx", -0.3), F("cy", -5.6), F("cz", 1.55)))
    LOOK = Vector((F("lx", 1.8), F("ly", 0.5), F("lz", 0.55)))
    cam_d.shift_x, cam_d.shift_y = F("shx", 0.0), F("shy", -0.12)     # round 3 extras: lower (was -0.22), nearer the middle
cam.location = CAM0
cam.rotation_euler = (LOOK - CAM0).to_track_quat("-Z", "Y").to_euler()

sun_d = bpy.data.lights.new("sun", "SUN")
sun_d.energy = 3.2
sun_d.angle = math.radians(6)
sun = bpy.data.objects.new("sun", sun_d)
sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
fill_d = bpy.data.lights.new("fill", "AREA")
fill_d.energy = 90
fill_d.size = 4
fill = bpy.data.objects.new("fill", fill_d)
sc.collection.objects.link(fill)
fill.location = (-3.5, -4.5, 2.5)
fill.rotation_euler = (LOOK - fill.location).to_track_quat("-Z", "Y").to_euler()
world = bpy.data.worlds.new("w")
sc.world = world
world.use_nodes = True
bgn = world.node_tree.nodes["Background"]
bgn.inputs["Color"].default_value = (0.75, 0.8, 0.9, 1)
bgn.inputs["Strength"].default_value = 0.55

res = int(F("res", 960))
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = res if LONG else res * 9 // 16
sc.render.resolution_y = res * 9 // 16 if LONG else res
sc.render.resolution_percentage = 100
sc.render.film_transparent = True
sc.render.dither_intensity = 0.0
sc.render.filter_size = 0.8
sc.eevee.taa_render_samples = int(F("samples", 16))
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.media_type = "IMAGE"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.fps = FPS


# ------------------------------------------------------------------ motion
def key_value(keys, t):
    """keys: [(t, value, ease)] where ease in 'io' (smooth) or 'in' (accelerate) applies to the segment ENDING at that key."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0, _), (t1, v1, e) in zip(keys, keys[1:]):
        if t <= t1:
            u = (t - t0) / max(1e-6, t1 - t0)
            u = u * u if e == "in" else ss(u)
            return lerp(v0, v1, u)
    return keys[-1][1]


def arm_keys():
    k = [(0.0, ARM_REST, "io")]
    prev = ARM_REST
    for tc in HITS:
        s = tc - 0.24
        if tc == T_BREAK:          # last swing: pulls back further, holds 3 frames, then the fastest strike
            k += [(s, prev, "io"), (s + 0.13, ARM_PULL, "io"), (tc - 0.05, ARM_PULL, "io"), (tc, ARM_HIT, "in"), (tc + 0.05, ARM_HIT, "io")]
        else:
            k += [(s, prev, "io"), (s + 0.15, ARM_UP, "io"), (s + 0.17, ARM_UP, "io"), (tc, ARM_HIT, "in"), (tc + 0.05, ARM_HIT, "io")]
        prev = ARM_HIT
    t = T_BREAK
    k += [(t + 0.16, ARM_READY - 12.0, "io"), (t + 0.40, ARM_READY, "io")]
    for tc in TAPS:                    # pointing round: short proud taps, a small lift and a quick drop onto the bar top
        k += [(tc - 0.13, ARM_READY, "io"), (tc - 0.06, F("tapup", -62.0), "io"), (tc, ARM_HIT, "in"), (tc + 0.04, ARM_HIT, "io"),
              (tc + 0.13, ARM_READY, "io")]
    k += [(T_END, ARM_READY, "io")]
    return k


ARMK = arm_keys()
for i in range(1, len(ARMK)):          # keys must be non-decreasing in time
    assert ARMK[i][0] >= ARMK[i - 1][0] - 1e-9, (i, ARMK[i - 1], ARMK[i])
MINE0 = HITS[0] - 0.26                 # the arm leaves the walk swing and starts the first wind-up

POINT = F("point", -58.0)              # left arm aimed forward-down at the green bar (higher covers the face)
PTK = [(0.0, 0.0, "io"), (P0, 0.0, "io"), (P0 + 0.09, POINT - 16.0, "io"), (P0 + 0.18, POINT, "io")]   # quick raise, small overshoot
for tj in JABS:                        # each pump: out a bit higher and back
    PTK += [(tj - 0.05, POINT, "io"), (tj, POINT - 18.0, "io"), (tj + 0.08, POINT, "io")]
PTK.append((T_END, POINT, "io"))
# head: (time, yaw, pitch). Yaw + = towards the camera, pitch + = looks down. Glance after the rank-up, then the pointing beats.
HEADK = [(0.0, 0, 0), (T_TAG + 0.12, 0, 0), (T_TAG + 0.22, 55, 0), (P0, 55, 0),
         (P0 + 0.10, 0, 18), (P0 + 0.20, 0, 18), (P0 + 0.28, 55, 0),          # "look at it!" then back to the viewer for the sneaks
         (P0 + 0.86, 55, 0), (P0 + 0.94, 5, 22), (P0 + 1.48, 5, 22),           # watches his own taps
         (P0 + 1.56, 55, -4), (P0 + 2.40, 55, -4),                             # hops facing the viewer
         (P0 + 2.46, 0, 16), (P0 + 2.54, 0, 16), (P0 + 2.60, 55, 0),          # double-take at the bar, then back to the viewer
         (T_END, 55, 0)]                                                        # sneak-spam burst 2 (no nods: the sneaks are the "yes")
for L_ in (PTK, HEADK):
    for i in range(1, len(L_)):
        assert L_[i][0] >= L_[i - 1][0] - 1e-9, (i, L_[i - 1], L_[i])
HYAW = [(k_[0], k_[1], "io") for k_ in HEADK]
HPIT = [(k_[0], k_[2], "io") for k_ in HEADK]


def steve_x(t):
    if t < T_ARR:
        u = max(0.0, t - START) / (T_ARR - START)
        return X0 + (SX - X0) * (1 - (1 - u) ** 2.2)          # enters at full speed, eases to a stop
    return SX


def pop_k(t):
    """Pop-out at the end: swells to 112%, then shrinks to nothing by T_END."""
    u = (t - TP) / POP
    if u <= 0:
        return 1.0
    return lerp(1.0, 1.12, ss(u / 0.35)) if u < 0.35 else lerp(1.12, 0.0, ss((u - 0.35) / 0.65))


def grn_squash(t):
    """Green bar squash: on each tap (strong) and each little-hop landing (soft). Returns (wider, lower)."""
    q = 0.0
    for tc, s in [(tc, 1.0) for tc in TAPS] + [(t0 + air, 0.45) for t0, air, _ in JUMPS[1:]]:
        d = t - tc
        if 0.0 <= d < 0.12:
            q = max(q, s * (1.0 - ss(d / 0.12)))
    return 1.0 + 0.05 * q, 1.0 - 0.12 * q


def crouch_amt(t):
    """The game's sneak is on or off, no in-between (the model pose is a yes/no flag): 1 while the key is held, else 0."""
    for t0 in CROUCH:
        if t0 <= t < t0 + CR_DN:
            return 1.0
    return 0.0


def hop_z(t):
    """The game's jump: a plain parabola, legs still, arms keep their pose."""
    for t0, air, hh in JUMPS:
        u = (t - t0) / air
        if 0.0 <= u <= 1.0:
            return hh * 4.0 * u * (1.0 - u)
    return 0.0


def anim_time(tv):
    """Scene time with the impact freeze: everything holds FRZ at the break contact."""
    if tv < T_BREAK:
        return tv
    return max(T_BREAK, tv - FRZ)


def walk_state(t):
    x = steve_x(t)
    dx = (steve_x(t + 0.01) - steve_x(t - 0.01)) / 0.02
    moving = min(1.0, abs(dx) / 2.2)
    dist = abs(x - X0)
    return x, moving, dist / 1.9 + (0.75 if LONG else 0.0)    # long: 3/4 cycle in, so the pickaxe arm is fully BACK as he enters


# XP orbs: the game's own sprite sheet (entity/experience_orb.png, 4x4 icons of 16 px), tinted green-yellow like the game, unlit
random.seed(11)
ORBS = []


def orb_obj(k, icon):
    me = bpy.data.meshes.new("orb%d" % k)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    hh = 0.5
    vs = [bm.verts.new(c) for c in ((-hh, 0, -hh), (hh, 0, -hh), (hh, 0, hh), (-hh, 0, hh))]
    f = bm.faces.new(vs)
    u0, v0 = (icon % 4) / 4.0, 1 - (icon // 4 + 1) / 4.0
    for lp, uv in zip(f.loops, [(u0, v0), (u0 + 0.25, v0), (u0 + 0.25, v0 + 0.25), (u0, v0 + 0.25)]):
        lp[uvl].uv = uv
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("orb%d" % k, me)
    sc.collection.objects.link(o)
    m = bpy.data.materials.new("orb%d" % k)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(os.path.join(TEXD, "experience_orb.png"), check_existing=True)
    tx.interpolation = "Closest"
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1
    nt.links.new(tx.outputs["Color"], mul.inputs[6])
    nt.links.new(mul.outputs[2], em.inputs["Color"])
    nt.links.new(tx.outputs["Alpha"], mx.inputs["Fac"])
    nt.links.new(tr.outputs["BSDF"], mx.inputs[1])
    nt.links.new(em.outputs["Emission"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    m.surface_render_method = "DITHERED"
    o.data.materials.append(m)
    o.visible_shadow = False
    return o, mul.inputs[7]


N_ORB = 7 if LONG else 6
for k in range(N_ORB):
    o, tint = orb_obj(k, random.choice((3, 4, 5, 6)))
    ORBS.append(dict(o=o, tint=tint, p=Vector((random.uniform(0.3, BW - 0.3), random.uniform(0.3, 0.55), BH * 0.6)),
                     v=Vector((random.uniform(-0.9, 0.9), random.uniform(-0.6, 0.1), random.uniform(2.6, 3.8))),
                     t_home=0.13 + 0.07 * k + random.uniform(-0.02, 0.02), dur=random.uniform(0.28, 0.36),
                     size=random.uniform(0.30, 0.39), ph=random.uniform(0, 6.28)))


def orb_pos(ob, a, target):
    """Ballistic burst (gravity 10), then pulled to the target with an accelerating ease (the game's orbs speed up near the player)."""
    p = ob["p"] + ob["v"] * a + Vector((0, 0, -0.5 * 10.0 * a * a))
    if a <= ob["t_home"]:
        return p, False
    u = min(1.0, (a - ob["t_home"]) / ob["dur"])
    a0 = ob["t_home"]
    p0 = ob["p"] + ob["v"] * a0 + Vector((0, 0, -0.5 * 10.0 * a0 * a0))
    return p0 + (target - p0) * (u ** 2.2), u >= 1.0


def push_amt(tv):
    """Camera push-in: starts with the last pull-back, full at the contact, holds through the freeze and the snap, eases back."""
    a = ss((tv - (T_BREAK - 0.10)) / 0.10)
    b = 1 - ss((tv - (T_BREAK + FRZ + 0.30)) / 0.70)
    return a * b


SHAKE_DIR = [(1.0, 0.55), (-0.85, -0.35), (0.6, -0.75), (-0.55, 0.6), (0.4, 0.3), (-0.3, -0.35), (0.2, 0.15), (-0.1, -0.1)]


def shake_off(tv):
    """8 frames (30 fps) of shake from the break contact, fading: one fixed direction per frame, like a hit-stop."""
    d = tv - T_BREAK
    for tc in HITS[:-1]:                         # round 3 extras: a small 4-frame shake on every other hit
        dh = tv - tc + 1e-6
        if 0 <= dh < 4 / 30.0:
            n = int(dh * 30)
            amp = F("hshake", 0.03) * (1 - n / 4.0)
            sx, sz = SHAKE_DIR[n]
            return Vector((sx * amp, 0, sz * amp))
    if d < 0 or d >= 8 / 30.0:
        return Vector((0, 0, 0))
    n = int(d * 30)
    amp = F("shake", 0.07) * (1 - n / 8.0) ** 1.5
    sx, sz = SHAKE_DIR[n]
    return Vector((sx * amp, 0, sz * amp))


def set_frame(f):
    tv = f / (FPS * SLOW) + START                # real (video) scene time; SLOW stretches the whole thing
    t = anim_time(tv)                            # frozen during the impact freeze
    frozen = T_BREAK <= tv < T_BREAK + FRZ
    x, moving, walk_phase = walk_state(t)
    leg = 42.0 * math.sin(2 * math.pi * walk_phase) * moving
    th = key_value(ARMK, t)
    mining = ss((t - MINE0) / 0.12)
    # right arm (holds the pickaxe): the game's item arm, fixed hold, no wrist. Long walk-in: a full walk swing that starts BACK,
    # so the body enters before the tool. Otherwise the game's item-arm walk (rest pose + half swing).
    full_sw = -42.0 * math.sin(2 * math.pi * walk_phase) * moving
    walk_arm = full_sw if LONG else ARM_REST + 0.5 * full_sw
    armR = lerp(walk_arm, th, ss((t - MINE0) / 0.10))
    armL = 42.0 * math.sin(2 * math.pi * walk_phase) * moving + (-8 * mining)
    armL = lerp(armL, key_value(PTK, t), ss((t - P0) / 0.06))     # pointing round: the free hand points at the green bar
    lean = (lerp(5.0, 0.0, ss((th - ARM_PULL) / (ARM_HIT - ARM_PULL))) if th < -30 else 0.0) * mining   # + = back (wind-up), - = forward (hit)
    hit_w = 0.0
    for tc in HITS:
        hit_w = max(hit_w, 1.0 - min(1.0, abs(t - (tc + 0.03)) / 0.10))
    # long walk-in: the first wind-up starts from the walk swing (arm back), so the arm sweeps forward past the bar end.
    # A short outward roll carries the pick head past the side of the bar instead of through it.
    roll = F("roll", 35.0) * ss((t - MINE0 + 0.02) / 0.04) * (1 - ss((t - MINE0 - 0.10) / 0.06)) if LONG else 0.0
    # the game's sneak (HumanoidModel, crouching): body tips 0.5 rad forward from the neck, arms +0.4 rad, head drops but stays
    # upright, legs move 4 px back, the whole player sits 2 px lower. Our body pivots at the hip, so it is matched by moving the hip.
    cr = crouch_amt(t)
    crl = 28.65 * cr                               # 0.5 rad; hip pitch + tips the body forward (checked in stills)
    arm_cr = (28.65 - 22.92) * cr                  # arms: the game adds 0.4 rad (abs); the body already gives 0.5 rad, so 0.1 rad back (+ = back)
    rot(steve["armR"], (armR + arm_cr + F("crarmR", -50.0) * cr, roll, 0))   # the pickaxe arm lifts while sneaking, so the pick stays out of the bar
    rot(steve["armL"], (armL + arm_cr, F("ptroll", 0.0) * ss((t - P0) / 0.06), 0))
    rot(steve["elbowR"], (0, 0, 0))              # the game's arm is one straight piece
    rot(hand, (0, 0, 0))
    rot(steve["elbowL"], (-6 * moving, 0, 0))
    rot(steve["legR"], (leg, 0, 0))
    rot(steve["legL"], (-leg, 0, 0))
    rot(steve["kneeR"], (max(0.0, -leg) * 0.6, 0, 0))
    rot(steve["kneeL"], (max(0.0, leg) * 0.6, 0, 0))
    rot(steve["hip"], (lean + crl, 0, 0))
    # neck ends 4 px ahead of the legs and 3 px lower (the game's numbers): hip goes 1.74 px back and 1.54 px down
    steve["hip"].location = Vector((0, 1.74 * cr, 12 - 1.54 * cr)) * PX       # +y = his back
    steve["head"].location = Vector((0, 0, 12 - 1.0 * cr)) * PX                 # the head drops 1 px more than the neck
    hy = key_value(HYAW, t) * F("glance", 55.0) / 55.0                           # look at the viewer / at the bar (HEADK)
    hloc = Euler((math.radians(5.0 * hit_w * mining + key_value(HPIT, t)), 0, math.radians(hy))).to_matrix()
    steve["head"].rotation_euler = (Matrix.Rotation(-math.radians(crl), 3, "X") @ hloc).to_euler("XYZ")   # head stays upright in a sneak
    rot(steve["root"], (0, 0, -90.0))
    hz = hop_z(t)
    pk = pop_k(t)
    steve["base"].location = (x + 4 * PX * cr, STEVE_Y, BASEZ + hz - 2 * PX * cr)   # sneak: legs 4 px back (he faces -x), 2 px lower
    steve["base"].scale = (max(pk, 1e-3),) * 3                                   # pop-out shrinks him to his feet
    GLINT.inputs["Location"].default_value = (0, -0.22 * tv, 0.05 * tv)     # the glint slides slowly, also during the freeze

    # ---- the bar, cracks, green bar
    shake = 0.012 * hit_w * (1 if (f % 4 < 2) else -1)
    show_blk = t < T_BREAK or frozen
    BLK.hide_render = not show_blk
    gu = (tv - START) / (2 / 30.0)                 # round 3 extras: faster pop, 2 frames up to the overshoot, 2 frames to settle
    grow_in = lerp(0.2, 1.12, ss(gu)) if gu < 1 else lerp(1.12, 1.0, ss(gu - 1))
    BLK.location = Vector((BAR_C.x + shake, BAR_C.y, BH / 2 * grow_in))                         # grows from its bottom edge
    BLK.scale = (grow_in,) * 3
    if frozen:                                   # squash on the break hit (the 2 freeze frames): wider and lower, on the ground
        BLK.scale = (grow_in * 1.06, grow_in, grow_in * 0.84)
        BLK.location = Vector((BAR_C.x + shake, BAR_C.y, BH / 2 * grow_in * 0.84))
    for tc in HITS[:-1]:                         # round 3 extras: smaller squash on every other hit too (2 frames at 30 fps)
        d = tv - tc
        if -1e-6 <= d < 2 / 30.0:
            q = 1.0 if d < 1 / 30.0 - 1e-6 else 0.5
            BLK.scale = (grow_in * (1 + 0.04 * q), grow_in, grow_in * (1 - 0.10 * q))
            BLK.location = Vector((BAR_C.x + shake, BAR_C.y, BH / 2 * grow_in * (1 - 0.10 * q)))
    stage = None
    if t >= HITS[0]:                             # the game's 10 crack stages grow steadily while mining; stage 9 on the break hit
        stage = min(9, int(10 * (t - HITS[0]) / (T_BREAK - HITS[0])))
    TXT.hide_render = not (show_blk and stage is not None)
    TXT.location = BLK.location
    TXT.scale = BLK.scale
    for CK in CRKS:
        CK.hide_render = not (show_blk and stage is not None)
        if stage is not None:
            CK.data.materials[0] = crack_mats[stage]
        CK.location = BLK.location
        CK.scale = BLK.scale
    DROP.hide_render = True                      # round 2: no dropped mini bar, the green bar snaps straight in on the burst
    tg = t - T_BREAK
    grn_on = (not show_blk) and pk > 0.02
    GRN.hide_render = not grn_on
    s_ = 0.0
    if grn_on:
        u = tg / SNAP
        pop = lerp(0.55, 1.10, ss(u / 0.5)) if u < 0.5 else lerp(1.10, 1.0, ss((u - 0.5) / 0.5))
        s_ = max(1e-3, pop * pk)
        qx, qz = grn_squash(t)                                         # taps and landings squash it a little
        GRN.location = Vector((BAR_C.x, BAR_C.y, BH / 2 * s_ * qz))
        GRN.rotation_euler = (0, 0, 0)
        GRN.scale = (s_ * qx, s_, s_ * qz)
    fl = grn_on and tg < F("flashs", 0.9 / 30.0) / SLOW        # white flash as the green bar bursts in: 1 frame at 30 fps (2 at 60), never 2 at 30
    FLASH.hide_render = FLASH_IN.hide_render = not fl            # star burst, placed with the billboards below
    # ---- solid pixel shadows (opaque, so they key cleanly)
    bar_s = grow_in if show_blk else s_
    SH_BAR.hide_render = bar_s < 0.05
    SH_BAR.scale = (max(bar_s, 1e-3),) * 3
    SH_STEVE.location = (x, STEVE_Y, 0.004)
    SH_STEVE.hide_render = pk < 0.05
    SH_STEVE.scale = (max(1e-3, pk * (1.0 - 0.45 * hz / max(HOP_H, 1e-3))),) * 3   # shadow shrinks while he is in the air

    # ---- debris
    for pc in PIECES:
        a = t - pc["t0"]
        o = pc["o"]
        if a < 0 or a > pc["life"] or (frozen and pc["t0"] == T_BREAK):
            o.hide_render = True
            continue
        o.hide_render = False
        pos = pc["p"] + pc["v"] * a + Vector((0, 0, -0.5 * 14.0 * a * a))
        o.location = pos
        o.rotation_euler = (pc["spin"].x * a, pc["spin"].y * a, pc["spin"].z * a)
        k = pc["size"] * (1.0 - ss((a - (pc["life"] - 0.18)) / 0.18))
        o.scale = (max(k, 1e-3),) * 3

    # ---- name tag + XP orbs: billboards that face the camera
    upd()
    face = (cam.rotation_euler.to_quaternion() @ Euler((-math.pi / 2, 0, 0)).to_quaternion()).to_euler()
    if fl:                                       # star burst in front of the bar's face, grows over its 1 frame (2 at 60 fps)
        g = F("starsz", 1.0) * (0.85 + 0.30 * min(1.0, tg / (0.9 / 30.0)))
        for k, S in enumerate((FLASH, FLASH_IN)):
            S.location = Vector((BAR_C.x, BAR_C.y - BD / 2 - 0.10 - 0.02 * k, BH / 2))
            S.rotation_euler = face
            S.scale = (BW * 0.62 * g, 1.0, BH * 1.15 * g)
    legend = t >= T_TAG
    TAG_N.hide_render = legend
    TAG_L.hide_render = not legend
    pu = (t - T_TAG) / 0.10
    pun = (lerp(0.6, 1.3, ss(pu)) if pu < 1 else lerp(1.3, 1.0, ss((pu - 1) / 1.6))) if legend else 1.0
    # bigger tag keeps its gap; round 3: the gap also grows while the tag pops past full size, so it never sits on the head
    hp = steve["head"].matrix_world.translation + Vector((0, 0, 0.74 + 0.15 * (F("tagk", 1.3) - 1.0) + 0.20 * max(0.0, pun - 1.0)))
    TAG_L_EM.default_value = 2.4 if (legend and t - T_TAG < 2 / 30.0) else (F("crtag", 0.5) if crouch_amt(t) > 0 else 1.0)  # 2-frame flash on the rank-up; the game dims a sneaking player's name tag
    for sp in SPARKS:
        a = t - T_TAG
        on = legend and a < 0.30
        sp["o"].hide_render = not on
        if on:
            c, s = sp["d"].x, sp["d"].z / 0.75     # round 3: start on a ring outside the tag box, so no spark lands on the letters or reads as editor handles
            sp["o"].location = hp + Vector((c * (0.85 * pun + sp["sp"] * a), 0, s * (0.34 * pun + 0.7 * sp["sp"] * a)))
            sp["o"].rotation_euler = face
            k = sp["size"] * (1.0 - ss((a - 0.15) / 0.15))
            sp["o"].scale = (max(k, 1e-3),) * 3
    for T in (TAG_N, TAG_L):
        T.location = hp
        T.rotation_euler = face
        T.scale = (max(pun * pk, 1e-3),) * 3
    TAG_L.hide_render = TAG_L.hide_render or pk < 0.02
    tip = Vector((BW - 0.25, BAR_C.y - BD / 2 - 0.05, BH))       # the struck spot on the green bar's top front edge
    for hs in HAPPY:                             # green sparkles fly up and out from each tap, then fade (0.40 s)
        a = t - hs["t0"]
        on = 0.0 <= a < 0.40
        hs["o"].hide_render = not on
        if on:
            hs["o"].location = tip + hs["d"] * (0.10 + hs["sp"] * a) + Vector((0, 0, -1.6 * a * a))
            hs["o"].rotation_euler = face
            k = hs["size"] * ss(a / 0.04) * (1.0 - ss((a - 0.22) / 0.18))
            hs["o"].scale = (max(k, 1e-3),) * 3
    chest = steve["hip"].matrix_world.translation + Vector((0, 0, 0.45))
    for ob in ORBS:
        a = t - T_BREAK
        o = ob["o"]
        if a <= 0 or frozen:
            o.hide_render = True
            continue
        p, gone = orb_pos(ob, a, chest)
        o.hide_render = gone
        o.location = p
        o.rotation_euler = face
        ticks = a * 20 + ob["ph"]
        r = (math.sin(ticks / 2.0) + 1) * 0.5
        b = (math.sin(ticks / 2.0 + 4.1887903) + 1) * 0.1
        glow = 1.0 + F("orbglow", 0.6) * (0.5 + 0.5 * math.sin(ticks))          # brightness pulse (emission above 1)
        ob["tint"].default_value = (r ** 2.2 * glow, glow, b ** 2.2 * glow, 1)
        o.scale = (ob["size"] * ss(a / 0.06) * (1.0 + 0.12 * math.sin(ticks)),) * 3

    # ---- camera: push-in on the last swing + shake on the break
    cam.location = CAM0 + (LOOK - CAM0) * (F("push", 0.10) * push_amt(tv)) + shake_off(tv)
    if LONG:                                     # round 3 extras: 15% bigger while the top is empty, eases back out on the break (reveal)
        z = 1.0 - ss((tv - T_BREAK) / F("zoomout", 0.35))
        cam_d.lens = F("lens", 36) * (1.0 + F("zoomk", 0.15) * z)
        cam_d.shift_y = F("shy", 0.0) - F("zoomsh", 0.03) * z     # lifts the bar off the bottom edge while zoomed


def events():
    """Sound event times in VIDEO seconds (frame 0 = 0), written next to the frames for make_video.py."""
    vt = lambda t: ((t - START) if t < T_BREAK else (t - START + FRZ)) * SLOW     # noqa: E731
    ev = {"hits": [round((tc - START) * SLOW, 4) for tc in HITS[:-1]], "break": round((T_BREAK - START) * SLOW, 4),
          "burst": round((T_BREAK - START + FRZ) * SLOW, 4), "tag": round(vt(T_TAG), 4)}
    steps, last = [], None
    t = START
    while t < T_END:
        _, moving, ph = walk_state(t)
        n = int(ph * 2)
        if last is not None and n != last and moving > 0.3:
            steps.append(round(vt(t), 4))
        last = n
        t += 1 / 240.0
    ev["steps"] = sorted(steps)
    ev["lands"] = [round(vt(t0 + air), 4) for t0, air, _ in JUMPS]
    ev["taps"] = [round(vt(tc), 4) for tc in TAPS]
    ev["bar_in"] = 0.0
    ev["bar_out"] = round(vt(TP + 0.35 * POP), 4)          # the pop-out sound on the swell peak, as it all starts to vanish
    ev["orbs"] = sorted(round(vt(T_BREAK + ob["t_home"] + ob["dur"]), 4) for ob in ORBS)
    ev["end"] = round(vt(T_END), 4)
    return ev


if __name__ == "__main__":
    import json
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "events.json"), "w") as fh:
        json.dump(events(), fh, indent=1)
    if "still" in OPT:
        fr = [int(F("still", 0))]
    else:
        a, b = (OPT.get("frames") or "0-%d" % int(round((T_END - START + FRZ) * FPS * SLOW))).split("-")
        fr = list(range(int(a), int(b) + 1, int(F("step", 2))))
    for f in fr:
        set_frame(f)
        if "probe" in OPT:                       # probe=1: print where the pickaxe is instead of rendering (hold checks)
            upd()
            vs = [pick.matrix_world @ v.co for v in pick.data.vertices]
            r3 = lambda v: tuple(round(c, 3) for c in v)     # noqa: E731
            print("PROBE", f, "pivot", r3(steve["armR"].matrix_world.translation), "grip", r3(hand.matrix_world.translation),
                  "lowest", r3(min(vs, key=lambda v: v.z)), "front", r3(min(vs, key=lambda v: v.x)), "top", r3(max(vs, key=lambda v: v.z)))
            bar_on = not BLK.hide_render or not GRN.hide_render
            ins = [BW - v.x for v in vs if v.x < BW and v.z < BH and 0.25 < v.y < 0.75] if bar_on else []
            print("CLIP", f, "bar" if bar_on else "-", len(ins), round(max(ins), 3) if ins else 0, "low_z", round(min(v.z for v in vs), 3))
            if F("probe", 1) > 1:
                print("AXES", [r3(c) for c in hand.matrix_world.to_3x3().col], "pickbasis", [r3(c) for c in pick.matrix_basis.to_3x3().col],
                      "armR", r3(steve["armR"].rotation_euler), "hip", r3(steve["hip"].rotation_euler))
            continue
        sc.render.filepath = os.path.join(OUTDIR, "f%04d.png" % f)
        bpy.ops.render.render(write_still=True)
    print("done", len(fr))
