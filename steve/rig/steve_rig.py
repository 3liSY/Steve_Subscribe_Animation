"""steve_rig.py - the Minecraft player rig used by steve_scene.py: skin material, box and voxel limbs, bendable arms and legs, block material.
Not run on its own: steve_scene.py loads this file and executes it in its own namespace."""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

D = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.join(D, "thumb.png")
TEX = os.path.join(D, "tex189")  # 1.8.9 textures = the classic look the 2012 map was played with
PX = 1 / 16
E1 = lambda k, d: float(os.environ.get(k, d))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


# ---------------------------------------------------------------- characters
def skin_mat(name, path, ao=True):
    ao_on = ao
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tx = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(path)
    img.alpha_mode = "STRAIGHT"
    tx.image = img
    tx.interpolation = "Closest"
    bs.inputs["Roughness"].default_value = 0.85  # matte, like the game - no plastic sheen on the suits/hair
    bs.inputs["Specular IOR Level"].default_value = 0.25
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")   # v10: contact shadows between limbs = 3D volume
    ao.samples = 16
    ao.inputs["Distance"].default_value = float(os.environ.get("CHAO", 0.35)) if ao_on else 1e-4
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = float(os.environ.get("CHAOPOW", 1.6))
    nt.links.new(ao.outputs["AO"], pw.inputs[0])
    mao = nt.nodes.new("ShaderNodeMix")
    mao.data_type, mao.blend_type = "RGBA", "MULTIPLY"
    mao.inputs["Factor"].default_value = 1
    nt.links.new(tx.outputs["Color"], mao.inputs[6])
    nt.links.new(pw.outputs[0], mao.inputs[7])
    nt.links.new(mao.outputs[2], bs.inputs["Base Color"])
    nt.links.new(tx.outputs["Alpha"], bs.inputs["Alpha"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m


def box(name, size, uv, mat, grow=0.0, skip_front=False, texsize=(64, 64), rows=None):
    """Minecraft skin cuboid. Local front is -Y, the player's right is -X.
    rows=(r0, r1): only texture rows r0..r1 of a limb of full height size[1] (a bendable segment);
    the overlay only grows past the limb's real ends, and inner caps are left open."""
    w, h, d = size
    r0, r1 = rows if rows else (0, h)
    hh = r1 - r0
    x0, x1 = -(w / 2 + grow) * PX, (w / 2 + grow) * PX
    y0, y1 = -(d / 2 + grow) * PX, (d / 2 + grow) * PX
    z0 = -(hh / 2 + (grow if r1 >= h else 0)) * PX
    z1 = (hh / 2 + (grow if r0 <= 0 else 0)) * PX
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    V = lambda x, y, z: bm.verts.new((x, y, z))
    lbf, rbf, rtf, ltf = V(x0, y0, z0), V(x1, y0, z0), V(x1, y0, z1), V(x0, y0, z1)
    lbb, rbb, rtb, ltb = V(x0, y1, z0), V(x1, y1, z0), V(x1, y1, z1), V(x0, y1, z1)
    u, v = uv

    def face(vs, rect):
        f = bm.faces.new(vs)
        ru, rv, rw, rh = rect
        # vs = texture bottom-left, bottom-right, top-right, top-left
        for lp, (pu, pv) in zip(f.loops, [(ru, rv + rh), (ru + rw, rv + rh), (ru + rw, rv), (ru, rv)]):
            lp[uvl].uv = (pu / texsize[0], 1 - pv / texsize[1])

    vr = v + d + max(r0, 0)
    hr = min(r1, h) - max(r0, 0)
    if not skip_front:
        face([lbf, rbf, rtf, ltf], (u + d, vr, w, hr))          # front
    face([rbb, lbb, ltb, rtb], (u + d + w + d, vr, w, hr))      # back
    face([lbb, lbf, ltf, ltb], (u, vr, d, hr))                  # player's right side (-X)
    face([rbf, rbb, rtb, rtf], (u + d + w, vr, d, hr))          # player's left side (+X)
    if r0 <= 0:
        face([ltf, rtf, rtb, ltb], (u + d, v, w, d))            # top
    if r1 >= h:
        face([lbb, rbb, rbf, lbf], (u + d + w, v, w, d))        # bottom
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


_PIXCACHE = {}


def _skin_pixels(mat):
    """the material's skin as an RGBA array, top row first (like the skin file)"""
    import numpy as np
    img = next(n.image for n in mat.node_tree.nodes if n.type == "TEX_IMAGE")
    if img.name not in _PIXCACHE:
        w_, h_ = img.size
        _PIXCACHE[img.name] = np.array(img.pixels[:], dtype=np.float32).reshape(h_, w_, 4)[::-1]
    return _PIXCACHE[img.name]


def vox_box(name, size, uv, mat, grow, skip_front=False, texsize=(64, 64), rows=None, vfrom=None):
    """3D second layer (VOX3D=1): every opaque overlay pixel is a solid block `grow` px thick sitting on the base box,
    instead of a thin shell floating `grow` px off it. Sleeve and shoe bands then read as solid straps, not paper strips
    hanging off the limb (the owner's "broken hands"). Same outer extent as box(..., grow). Corners are closed: front/back
    pixels reach over the side edges, top/bottom pixels reach over every edge. vfrom: the lower half of a bent limb carries
    only rows from the joint down, so a band in the joint overlap is not drawn twice (two copies crossed like an X)."""
    w, h, d = size
    r0, r1 = rows if rows else (0, h)
    hh = r1 - r0
    W, Dd, Hh, g = w / 2, d / 2, hh / 2, grow
    u, v = uv
    px = _skin_pixels(mat)
    sk = px.shape[1] / texsize[0]
    on = lambda U, V: px[int((V + 0.5) * sk), int((U + 0.5) * sk), 3] > 0.5
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    boxes = []   # (xmin, xmax, ymin, ymax, zmin, zmax, U, V)

    def zrow(k):   # limb row k -> z range of this segment (clipped)
        return max(-Hh, Hh - (k + 1 - r0)), min(Hh, Hh - (k - r0))

    k0, k1 = int(math.floor(max(r0, 0, vfrom or 0))), int(math.ceil(min(r1, h)))
    for k in range(k0, k1):
        za, zb = zrow(k)
        if zb - za < 1e-4:
            continue
        V = v + d + k
        for i in range(w):
            ex0 = -g if i == 0 else 0.0
            ex1 = g if i == w - 1 else 0.0
            if not skip_front and on(u + d + i, V):            # front (-Y): column i -> x from -W
                boxes.append((-W + i + ex0, -W + i + 1 + ex1, -Dd - g, -Dd, za, zb, u + d + i, V))
            if on(u + d + w + d + i, V):                        # back (+Y): column i -> x from +W
                boxes.append((W - i - 1 - ex1, W - i - ex0, Dd, Dd + g, za, zb, u + d + w + d + i, V))
        for i in range(d):
            if on(u + i, V):                                    # player's right (-X): column i -> y from +D
                boxes.append((-W - g, -W, Dd - i - 1, Dd - i, za, zb, u + i, V))
            if on(u + d + w + i, V):                            # player's left (+X): column i -> y from -D
                boxes.append((W, W + g, -Dd + i, -Dd + i + 1, za, zb, u + d + w + i, V))
    for cap, ok in (("top", r0 <= 0), ("bottom", r1 >= h)):
        if not ok:
            continue
        for i in range(w):
            for j in range(d):
                ex = (-g if i == 0 else 0.0, g if i == w - 1 else 0.0, -g if j == 0 else 0.0, g if j == d - 1 else 0.0)
                x0_, x1_ = -W + i + ex[0], -W + i + 1 + ex[1]
                if cap == "top":                                # row j -> y from +D (back) to front
                    U, V = u + d + i, v + j
                    y0_, y1_ = Dd - j - 1 - ex[3], Dd - j - ex[2]
                    zz = (Hh, Hh + g)
                else:                                           # row j -> y from -D (front) to back
                    U, V = u + d + w + i, v + j
                    y0_, y1_ = -Dd + j + ex[2], -Dd + j + 1 + ex[3]
                    zz = (-Hh - g, -Hh)
                if on(U, V):
                    boxes.append((x0_, x1_, y0_, y1_, zz[0], zz[1], U, V))
    for (xa, xb, ya, yb, za, zb, U, V) in boxes:
        cu, cv = (U + 0.5) / texsize[0], 1 - (V + 0.5) / texsize[1]
        P_ = [bm.verts.new((x * PX, y * PX, z * PX)) for z in (za, zb) for y in (ya, yb) for x in (xa, xb)]
        for q in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)):
            f = bm.faces.new([P_[t] for t in q])
            for lp in f.loops:
                lp[uvl].uv = (cu, cv)
    bm.to_mesh(me)   # each block is its own closed cube, wound outward
    bm.free()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


CAPE_WAVE = float(os.environ.get("CAPEWAVE", 10))
CAPE_TWIST = float(os.environ.get("CAPETWIST", 22))


def cape_cloth(name, mat, texsize=(46, 22)):
    """Vanilla cape box (10x16x1 px, outer design at UV (1,1)) as a continuous sheet: every pixel row is
    carried by a frame that bends (wave) and twists a little more than the row above - folds without gaps."""
    from mathutils import Matrix
    frames = [Matrix.Identity(4)]
    for i in range(1, 17):
        bend = math.radians(CAPE_WAVE * math.sin(i * 0.55 + 0.3))
        twist = math.radians(CAPE_TWIST / 16)
        frames.append(frames[-1] @ Matrix.Translation((0, 0, -PX)) @ Matrix.Rotation(bend, 4, "X") @ Matrix.Rotation(twist, 4, "Z"))
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.verify()
    grid = {}
    for i in range(17):
        for c in range(11):
            for sd, y in (("o", -0.5), ("i", 0.5)):
                grid[(sd, i, c)] = bm.verts.new(frames[i] @ Vector(((c - 5) * PX, y * PX, 0)))

    def quad(vs, uvs):
        f = bm.faces.new(vs)
        for lp, (u, v) in zip(f.loops, uvs):
            lp[uvl].uv = (u / texsize[0], 1 - v / texsize[1])

    for i in range(16):
        for c in range(10):
            # outer design: column c -> u = 1 + c, row i -> v = 1 + i
            quad([grid[("o", i + 1, c)], grid[("o", i + 1, c + 1)], grid[("o", i, c + 1)], grid[("o", i, c)]],
                 [(1 + c, 2 + i), (2 + c, 2 + i), (2 + c, 1 + i), (1 + c, 1 + i)])
            # inner side (mirrored like the box's back face)
            quad([grid[("i", i + 1, c + 1)], grid[("i", i + 1, c)], grid[("i", i, c)], grid[("i", i, c + 1)]],
                 [(21 - c, 2 + i), (22 - c, 2 + i), (22 - c, 1 + i), (21 - c, 1 + i)])
        # side edges (CAPEEDGE=design: the edge takes the colour of the design pixel next to it - a flag with clean edges)
        ed = os.environ.get("CAPEEDGE") == "design"
        quad([grid[("i", i + 1, 0)], grid[("o", i + 1, 0)], grid[("o", i, 0)], grid[("i", i, 0)]],
             [(1.3, 1.5 + i)] * 4 if ed else [(0, 2 + i), (1, 2 + i), (1, 1 + i), (0, 1 + i)])
        quad([grid[("o", i + 1, 10)], grid[("i", i + 1, 10)], grid[("i", i, 10)], grid[("o", i, 10)]],
             [(10.7, 1.5 + i)] * 4 if ed else [(11, 2 + i), (12, 2 + i), (12, 1 + i), (11, 1 + i)])
    ed = os.environ.get("CAPEEDGE") == "design"
    for c in range(10):
        quad([grid[("o", 0, c)], grid[("o", 0, c + 1)], grid[("i", 0, c + 1)], grid[("i", 0, c)]],
             [(1.5 + c, 1.3)] * 4 if ed else [(1 + c, 1), (2 + c, 1), (2 + c, 0), (1 + c, 0)])
        quad([grid[("i", 16, c)], grid[("i", 16, c + 1)], grid[("o", 16, c + 1)], grid[("o", 16, c)]],
             [(1.5 + c, 16.7)] * 4 if ed else [(11 + c, 1), (12 + c, 1), (12 + c, 0), (11 + c, 0)])
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    o.data.materials.append(mat)
    return o


def empty(name, parent=None, loc=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    sc.collection.objects.link(e)
    e.parent = parent
    e.location = Vector(loc) * PX
    return e


def rot(o, deg):
    o.rotation_euler = Euler([math.radians(a) for a in deg])


def player(tag, skin, pose, hide_hat_front=False, cape=None, cape_rot=(0, 0, 0)):
    """Returns the rig: base (feet, world placement + tilt), root (yaw), hip, head, arm/leg pivots."""
    mat = skin_mat(tag, skin, ao=False)
    mat_o = skin_mat(tag + "_o", skin, ao=True)
    r = {"meshes": []}
    r["base"] = empty(tag + "_base")
    r["root"] = empty(tag + "_root", r["base"])
    r["hip"] = empty(tag + "_hip", r["root"], (0, 0, 12))

    def part(nm, size, uv, uvo, par, rel, skip=False, rows=None, vfrom=None):
        for suffix, uu, g in (("", uv, 0), ("_o", uvo, 0.5)):
            use_ao = suffix and any(k in nm for k in os.environ.get("AOPARTS", "leg,arm,body").split(","))   # AO on the outer suit/limb layer only
            if suffix and os.environ.get("VOX3D") == "1":
                o = vox_box(tag + nm + suffix, size, uu, mat_o if use_ao else mat, g, skip_front=skip, rows=rows, vfrom=vfrom)
            else:
                o = box(tag + nm + suffix, size, uu, mat_o if use_ao else mat, g, skip_front=skip and suffix == "_o", rows=rows)
            o.parent = par
            o.location = Vector(rel) * PX
            r["meshes"].append(o)

    def limb(nm, size, uv, uvo, pivot, joint_name, top, split):
        """Two-segment limb hanging from its pivot: rows 0..split above the joint, split..h below it.
        top = how far the box reaches above the pivot (2 px for shoulders, 0 for hips).
        A bent joint gets 1.5 px of overlap so the outside of the bend has no notch."""
        w, h, d = size
        jz = top - split                                  # joint height relative to the pivot
        bend = abs(pose.get(joint_name, (0, 0, 0))[0])
        bent = bend > 5
        ov = 1.5 if bent else 0
        if bent and os.environ.get("JOINTOV") == "auto":   # solo v23: overlap grows with the bend so the outer corner stays closed
            ov = min(d / 2 * math.tan(math.radians(min(bend, 120)) / 2) + 0.4, split - 0.5)
        part(nm, size, uv, uvo, pivot, (0, 0, top - split / 2), rows=(0, split))
        r[joint_name] = empty(tag + "_" + joint_name, pivot, (0, 0, jz))
        lo_h = h - split + ov
        part(nm + "lo", size, uv, uvo, r[joint_name], (0, 0, ov - lo_h / 2), rows=(split - ov, h), vfrom=split)

    for side, uv, uvo, x in (("R", (0, 16), (0, 32), -2), ("L", (16, 48), (0, 48), 2)):
        r["leg" + side] = empty(tag + "_leg" + side, r["root"], (x, 0, 12))
        limb("leg" + side, (4, 12, 4), uv, uvo, r["leg" + side], "knee" + side, 0, 6)
    part("body", (8, 12, 4), (16, 16), (16, 32), r["hip"], (0, 0, 6))
    r["head"] = empty(tag + "_head", r["hip"], (0, 0, 12))
    part("head", (8, 8, 8), (0, 0), (32, 0), r["head"], (0, 0, 4), skip=hide_hat_front)
    for side, uv, uvo, x in (("R", (40, 16), (40, 32), -5.5), ("L", (32, 48), (48, 48), 5.5)):
        r["arm" + side] = empty(tag + "_arm" + side, r["hip"], (x, 0, 10))
        limb("arm" + side, (3, 12, 4), uv, uvo, r["arm" + side], "elbow" + side, 2, 6)
    if cape:  # OptiFine cape: vanilla 46x22 layout (HD file is just x2), 10x16x1 px, hung from the top of the back
        cmat = skin_mat(tag + "_cape", cape)
        r["cape"] = empty(tag + "_cape", r["hip"], (0, 2.8, 12))  # hung slightly off the back so the far arm never pokes through
        holder = empty(tag + "_capeflip", r["cape"])
        holder.rotation_euler = Euler((0, 0, math.pi))  # like the game: box front (outer design) faces backwards
        # flowing cape: one continuous cloth (11x17 vertex grid, 1 px thick) bent and twisted row by row
        o = cape_cloth(tag + "cape", cmat)
        o.parent = holder
        r["meshes"].append(o)
        rot(r["cape"], cape_rot)
    for k, deg in pose.items():
        rot(r[k], deg)
    return r


def upd():
    bpy.context.view_layer.update()


def wpt(obj, px_local):
    return obj.matrix_world @ (Vector(px_local) * PX)


def snap_feet(rig, leg_names):
    upd()
    zs = [(o.matrix_world @ v.co).z for o in rig["meshes"] if o.name[1:].startswith(tuple(leg_names)) for v in o.data.vertices]
    rig["base"].location.z -= min(zs)


# ---------------------------------------------------------------- blocks
def block_mat(name, tex, tint=(1, 1, 1), emit=0.0, alpha=False, rough=0.85, texdir=None, cam_only=False, depth_fall=None, ao_dist=0.0, deep=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = bpy.data.images.load(os.path.join(texdir or TEX, tex + ".png"), check_existing=True)
    tx.interpolation = "Closest"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1
    mix.inputs[7].default_value = (*tint, 1)
    nt.links.new(tx.outputs["Color"], mix.inputs[6])
    col_out = mix.outputs[2]
    if ao_dist:  # contact darkening in the block recesses: depth and contrast without darkening the colours
        ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao.samples = 12
        ao.inputs["Distance"].default_value = ao_dist
        pw = nt.nodes.new("ShaderNodeMath")
        pw.operation = "POWER"
        pw.inputs[1].default_value = 1.8
        nt.links.new(ao.outputs["AO"], pw.inputs[0])
        mao = nt.nodes.new("ShaderNodeMix")
        mao.data_type = "RGBA"
        mao.blend_type = "MULTIPLY"
        mao.inputs["Factor"].default_value = 1
        nt.links.new(col_out, mao.inputs[6])
        nt.links.new(pw.outputs[0], mao.inputs[7])
        col_out = mao.outputs[2]
    if deep:  # v14: the shaft darkens only far BELOW the ledge, so the drop reads deep (the wall behind the pair is untouched)
        z_lo, z_hi, f_lo = deep
        gp = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.clamp = True
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = z_lo, z_hi
        mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = f_lo, 1.0
        nt.links.new(gp.outputs["Position"], sep.inputs[0])
        nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
        md = nt.nodes.new("ShaderNodeMix")
        md.data_type, md.blend_type = "RGBA", "MULTIPLY"
        md.inputs["Factor"].default_value = 1
        nt.links.new(col_out, md.inputs[6])
        nt.links.new(mr.outputs["Result"], md.inputs[7])
        col_out = md.outputs[2]
    nt.links.new(col_out, bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = rough
    if emit:
        nt.links.new(col_out, bs.inputs["Emission Color"])
        bs.inputs["Emission Strength"].default_value = emit
        if cam_only:  # glow seen by the camera only - keeps the bands vivid without flooding the scene with light
            lp = nt.nodes.new("ShaderNodeLightPath")
            mul = nt.nodes.new("ShaderNodeMath")
            mul.operation = "MULTIPLY"
            mul.inputs[1].default_value = emit
            nt.links.new(lp.outputs["Is Camera Ray"], mul.inputs[0])
            out_s = mul.outputs[0]
            if depth_fall:  # deeper rows glow less: light falls off down the shaft
                z_lo, z_hi, f_lo = depth_fall
                gp = nt.nodes.new("ShaderNodeNewGeometry")
                sep = nt.nodes.new("ShaderNodeSeparateXYZ")
                mr = nt.nodes.new("ShaderNodeMapRange")
                mr.clamp = True
                mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = z_lo, z_hi
                mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = f_lo, 1.0
                nt.links.new(gp.outputs["Position"], sep.inputs[0])
                nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
                m2 = nt.nodes.new("ShaderNodeMath")
                m2.operation = "MULTIPLY"
                nt.links.new(out_s, m2.inputs[0])
                nt.links.new(mr.outputs["Result"], m2.inputs[1])
                out_s = m2.outputs[0]
            nt.links.new(out_s, bs.inputs["Emission Strength"])
    if alpha:
        nt.links.new(tx.outputs["Alpha"], bs.inputs["Alpha"])
    nt.links.new(bs.outputs["BSDF"], out.inputs["Surface"])
    return m


DIRS = {  # face normal -> quad corners (unit cube), ordered tex bottom-left, bottom-right, top-right, top-left
    (0, -1, 0): [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],
    (1, 0, 0): [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],
    (0, 1, 0): [(1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1)],
    (-1, 0, 0): [(0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)],
    (0, 0, 1): [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
    (0, 0, -1): [(0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)],
}


def build_blocks(world, kinds):
    """world: {(x,y,z): kind}. kinds: {kind: (opaque, {"top"|"side"|"bottom": material})}.
    Faces against opaque neighbours, and glass-to-same-glass faces, are culled like in game."""
    for kind, (opaque, mats) in kinds.items():
        me = bpy.data.meshes.new(kind)
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.verify()
        slots = list(dict.fromkeys(mats.values()))
        for p, k in world.items():
            if k != kind:
                continue
            for n, quad in DIRS.items():
                nb = world.get((p[0] + n[0], p[1] + n[1], p[2] + n[2]))
                if nb is not None and (kinds[nb][0] or nb == k):
                    continue
                vs = [bm.verts.new((p[0] + a, p[1] + b, p[2] + c)) for a, b, c in quad]
                f = bm.faces.new(vs)
                role = "top" if n == (0, 0, 1) else "bottom" if n == (0, 0, -1) else "side"
                f.material_index = slots.index(mats.get(role, mats["side"]))
                for lp, uv in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
                    lp[uvl].uv = uv
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(kind, me)
        sc.collection.objects.link(o)
        for m in slots:
            o.data.materials.append(m)


