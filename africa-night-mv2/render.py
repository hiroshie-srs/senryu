# -*- coding: utf-8 -*-
"""Render the 「アフリカの夜 / HIROSHIE」 lyric video (1920x1080, 24 fps).

    python3 make_panels.py              # once: cut panels out of the sheets
    python3 render.py                   # -> out/africa_no_yoru_HIROSHIE.mp4
    python3 render.py --stills 20,57    # preview frames
"""
import argparse
import math
import os
import re
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import timeline as TL  # noqa: E402

ASSETS = os.path.join(HERE, "assets")
FONT = os.path.join(HERE, "fonts", "NotoSerifCJK-Regular.ttc")
FONT_B = os.path.join(HERE, "fonts", "NotoSerifCJK-Bold.ttc")
OUT = os.path.join(HERE, "out")
W, H = 1920, 1080
FPS = 24
DURATION = 227.6
LYRIC_Y = 985
G = {}

# ============================================================================ helpers

def ease(p):
    p = min(max(p, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * p)


def ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def to_f(img):
    return np.asarray(img, np.float32) / 255.0


def to_img(a):
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))


def grade(img):
    """Warm 3D-animation look with a filmic touch: soft contrast, teal-tinted deep shadows, halation."""
    a = to_f(img.convert("RGB"))
    L = (a @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    a = L + (a - L) * 0.94
    sh = np.clip(1 - L * 2.2, 0, 1) ** 2
    a = a + sh * np.array([-0.02, 0.012, 0.035], np.float32)
    a = np.clip(a, 0, 1)
    a = 0.035 + 0.94 * (a + 0.10 * a * (1 - a) * (a - 0.3))  # gentle S + black lift
    bright = np.clip((L - 0.58) / 0.42, 0, 1) * a
    r = max(4, int(min(img.size) * 0.035))
    halo = to_f(to_img(bright).filter(ImageFilter.GaussianBlur(r)))
    halo2 = to_f(to_img(bright).filter(ImageFilter.GaussianBlur(r * 3)))
    a = a + halo * 0.45 + halo2 * 0.25 * np.array([1.0, 0.75, 0.5], np.float32)
    return to_img(a)


def find_glints(img, n=4, thr=0.90):
    a = to_f(img.convert("L").filter(ImageFilter.GaussianBlur(2)))
    pts = []
    work = a.copy()
    rad = max(10, min(img.size) // 18)
    for _ in range(n):
        i = int(np.argmax(work))
        y, x = divmod(i, work.shape[1])
        v = work[y, x]
        if v < thr:
            break
        pts.append((x, y, float(v)))
        work[max(0, y - rad):y + rad, max(0, x - rad):x + rad] = 0
    return pts


def star_sprite(size=160):
    yy, xx = np.mgrid[-size:size + 1, -size:size + 1].astype(np.float32) / size
    r = np.sqrt(xx ** 2 + yy ** 2) + 1e-6
    core = np.exp(-(r / 0.06) ** 2)
    glow = np.exp(-(r / 0.22) ** 2) * 0.35
    ray = lambda u, v: np.exp(-(np.abs(v) / 0.010) ** 1.2) * np.clip(1 - np.abs(u), 0, 1) ** 2.2
    rays = ray(xx, yy) + ray(yy, xx)
    d1, d2 = (xx + yy) / 1.414, (xx - yy) / 1.414
    rays += 0.35 * (ray(d1, d2) + ray(d2, d1)) * 0.6
    s = np.clip(core + glow + rays, 0, 1.5)
    return s


def disc_sprite(r=24):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32) / r
    return np.clip(1 - np.sqrt(xx ** 2 + yy ** 2), 0, 1) ** 1.6


def add_sprite(frame, spr, x, y, scale, color, amount):
    if amount <= 0.01:
        return
    s = max(4, int(spr.shape[0] * scale))
    s = int(round(s / 8.0)) * 8 + 1  # quantise so the cache stays small
    key = (id(spr), s)
    sp = G["sprite_cache"].get(key)
    if sp is None:
        sp = np.asarray(Image.fromarray((np.clip(spr, 0, 1.5) / 1.5 * 255).astype(np.uint8)).resize((s, s), Image.BILINEAR), np.float32) / 255 * 1.5
        G["sprite_cache"][key] = sp
    h = s // 2
    x0, y0 = int(x) - h, int(y) - h
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(W, x0 + s), min(H, y0 + s)
    if xa >= xb or ya >= yb:
        return
    sub = sp[ya - y0:yb - y0, xa - x0:xb - x0][..., None]
    frame[ya:yb, xa:xb] += sub * np.array(color, np.float32) * amount

# ============================================================================ sources

def load():
    src = {}
    pd = os.path.join(ASSETS, "panels")
    for f in sorted(os.listdir(pd)):
        name = f[:-4]
        src[name] = grade(Image.open(os.path.join(pd, f)))
    src["Y"] = grade(Image.open(os.path.join(ASSETS, "sheets", "yokohama.webp")))
    src["TALK"] = grade(Image.open(os.path.join(ASSETS, "sheets", "talk.webp")))
    src["FIST"] = grade(Image.open(os.path.join(ASSETS, "sheets", "fistbump.webp")))
    glints = {k: find_glints(v, n=(7 if k == "Y" else 5 if k in ("TALK", "FIST") else 4)) for k, v in src.items()}
    return src, glints


def bg_for(name, crop):
    """Blurred, darkened cover background (slightly oversized for parallax)."""
    key = (name, crop)
    if key in G["bg_cache"]:
        return G["bg_cache"][key].astype(np.float32) / 255.0
    img = G["src"][name]
    if crop:
        img = img.crop(crop)
    bw, bh = W + 120, H + 68
    sc = max(bw / img.width, bh / img.height)
    im = img.resize((int(img.width * sc) + 1, int(img.height * sc) + 1), Image.BILINEAR)
    l, t = (im.width - bw) // 2, (im.height - bh) // 2
    im = im.crop((l, t, l + bw, t + bh)).filter(ImageFilter.GaussianBlur(38))
    a = to_f(im) * 0.42 + np.array([0.02, 0.012, 0.0], np.float32)
    G["bg_cache"][key] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    return a

# ============================================================================ layouts

def shake(t, amp=1.0):
    return (amp * (1.4 * math.sin(t * 0.9) + 0.5 * math.sin(t * 2.3 + 1)),
            amp * (1.1 * math.sin(t * 1.1 + 2) + 0.4 * math.sin(t * 2.7)))


def place(frame, img, box_src, left, top, w, h, rot=0.0):
    """Resample box_src of img into a w x h rectangle at (left, top); returns mapping for glints."""
    w, h = int(round(w)), int(round(h))
    out = img.transform((w, h), Image.EXTENT, box_src, Image.BICUBIC)
    if rot:
        out = out.convert("RGBA").rotate(rot, Image.BICUBIC, expand=False)
        arr = to_f(out)
        rgb, al = arr[..., :3], arr[..., 3:4]
    else:
        rgb, al = to_f(out), None
    l, t = int(round(left)), int(round(top))
    xa, ya, xb, yb = max(0, l), max(0, t), min(W, l + w), min(H, t + h)
    if xa >= xb or ya >= yb:
        return
    sub = rgb[ya - t:yb - t, xa - l:xb - l]
    if al is None:
        frame[ya:yb, xa:xb] = sub
    else:
        a = al[ya - t:yb - t, xa - l:xb - l]
        frame[ya:yb, xa:xb] = frame[ya:yb, xa:xb] * (1 - a) + sub * a


def shadow(frame, left, top, w, h, strength=0.65, soft=40):
    xs = np.arange(W, dtype=np.float32)
    ys = np.arange(H, dtype=np.float32)
    def prof(v, a, b):
        return np.clip((v - (a - soft)) / (2 * soft), 0, 1) * np.clip(((b + soft) - v) / (2 * soft), 0, 1)
    m = np.outer(prof(ys, top + 18, top + h + 30), prof(xs, left + 6, left + w + 6))
    frame *= (1 - strength * m)[..., None]


def glint_draw(frame, name, mapper, t, gain=1.0):
    for k, (gx, gy, v) in enumerate(G["glints"].get(name, [])):
        p = mapper(gx, gy)
        if p is None:
            continue
        tw = 0.55 + 0.45 * math.sin(t * (1.6 + 0.37 * k) + k * 2.1)
        add_sprite(frame, G["star"], p[0], p[1], 0.55 + 0.25 * v, (1.0, 0.86, 0.62), 0.55 * tw * gain)


def layout_card(frame, t, p, prm):
    name = prm["p"]
    img = G["src"][name]
    crop = prm.get("crop")
    if crop:
        crop = (max(0, crop[0]), max(0, crop[1]), min(img.width, crop[2]), min(img.height, crop[3]))
    box = crop or (0, 0, img.width, img.height)
    sx, sy = shake(t)
    bg = bg_for(name, crop)
    ox = int(60 + sx * 2 - 30 * (p - 0.5))
    oy = int(34 + sy * 2)
    frame[:] = bg[oy:oy + H, ox:ox + W]
    if prm.get("dark"):
        frame *= 1 - prm["dark"]
    z0, z1 = prm.get("z", (1.0, 1.06))
    e = 0.2 * p + 0.8 * ease(p)
    z = z0 + (z1 - z0) * e
    ch = prm.get("h", 800) * z
    asp = (box[2] - box[0]) / (box[3] - box[1])
    cw = ch * asp
    if cw > 1500:
        cw = 1500 * z
        ch = cw / asp
    cx = prm.get("x", W / 2) + prm.get("dx", 0) * (e - 0.5) * 2 + sx
    cy = H / 2 - 62 + prm.get("dy", 0) * (e - 0.5) * 2 + sy
    left, top = cx - cw / 2, cy - ch / 2
    shadow(frame, left, top, cw, ch)
    rot = 0.0
    if prm.get("rot"):
        rot = prm["rot"][0] + (prm["rot"][1] - prm["rot"][0]) * e
    place(frame, img, box, left, top, cw, ch, rot)
    if prm.get("glow"):  # light spilling from the open door
        k = ease(p) * 0.25
        frame += k * np.array([1.0, 0.7, 0.35], np.float32) * G["center_glow"]

    def mapper(gx, gy):
        if not (box[0] <= gx < box[2] and box[1] <= gy < box[3]):
            return None
        return (left + (gx - box[0]) / (box[2] - box[0]) * cw, top + (gy - box[1]) / (box[3] - box[1]) * ch)
    glint_draw(frame, name, mapper, t)


def layout_fill(frame, t, p, prm):
    img = G["src"][prm["p"]]
    a, b = prm["a"], prm["b"]
    e = 0.2 * p + 0.8 * ease(p)
    cx, cy, w = (a[i] + (b[i] - a[i]) * e for i in range(3))
    w = min(w, img.width, img.height * 16 / 9)
    h = w * 9 / 16
    sx, sy = shake(t, 0.6)
    cx = min(max(cx + sx * w / W, w / 2), img.width - w / 2)
    cy = min(max(cy + sy * w / W, h / 2), img.height - h / 2)
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    place(frame, img, box, 0, 0, W, H)
    if prm.get("burst"):
        bx, by = prm["burst"]
        G["burst_xy"] = ((bx - box[0]) / w * W, (by - box[1]) / h * H)

    def mapper(gx, gy):
        X, Y = (gx - box[0]) / w * W, (gy - box[1]) / h * H
        return (X, Y) if 0 <= X < W and 0 <= Y < H else None
    glint_draw(frame, prm["p"], mapper, t, 0.8)


def layout_split(frame, t, p, prm, dur):
    ps = prm["ps"]
    n = len(ps)
    gap = 14
    colw = (W - gap * (n + 1)) / n
    frame[:] = np.array([0.045, 0.03, 0.022], np.float32)
    el = t - prm["_t0"]
    for i, name in enumerate(ps):
        img = G["src"][name]
        k = 1.0
        z = 1.0 + 0.03 * p
        colh = H - gap - 150
        # cover-fit the panel into the column
        asp = colw / colh
        if img.width / img.height > asp:
            bh = img.height / z
            bw = bh * asp
        else:
            bw = img.width / z
            bh = bw / asp
        cxs, cys = img.width / 2, img.height * 0.45
        box = (cxs - bw / 2, max(0, cys - bh / 2), cxs + bw / 2, max(0, cys - bh / 2) + bh)
        if box[3] > img.height:
            box = (box[0], img.height - bh, box[2], img.height)
        left = gap + i * (colw + gap)
        top = gap + (1 - k) * (90 if i % 2 == 0 else -90)
        place(frame, img, box, left, top, colw, colh)
        if k < 1:
            frame[:, int(left):int(left + colw)] *= (0.25 + 0.75 * k)
    frame[:gap] = frame[:gap] * 0 + np.array([0.045, 0.03, 0.022], np.float32)
    frame[H - 150:] = frame[H - 150:] * 0 + np.array([0.045, 0.03, 0.022], np.float32)


def layout_meet(frame, t, p, prm):
    """Two cards slide in from the sides, over the bar counter, and bump at `touch` seconds."""
    a, b = prm["ps"]
    el = t - prm["_t0"]
    touch = prm.get("touch", 1.5)
    k = ease_out(el / touch) if el < touch else 1.0
    # small recoil after the bump
    rec = 0.0
    if el >= touch:
        d = el - touch
        rec = 22 * math.exp(-d / 0.18) * math.cos(d * 18)
    bgA = bg_for(prm.get("bg", a), None)
    sx, sy = shake(t)
    frame[:] = bgA[34:34 + H, 60:60 + W] * 0.85
    ch = prm.get("h", 720) * (1 + 0.03 * p)
    top = H / 2 - ch / 2 - 62 + sy
    for j, name in enumerate((a, b)):
        img = G["src"][name]
        if j == 1 and prm.get("flip_right"):
            img = G["flip_cache"].setdefault(name, img.transpose(Image.FLIP_LEFT_RIGHT))
        cw = ch * img.width / img.height
        start = -cw * 0.3 if j == 0 else W - cw * 0.7
        end = W / 2 - cw - 4 if j == 0 else W / 2 + 4
        left = start + (end - start) * k + (-rec if j == 0 else rec) + sx
        shadow(frame, left, top, cw, ch)
        place(frame, img, (0, 0, img.width, img.height), left, top, cw, ch)
    if el >= touch:  # impact burst where the two meet
        d = el - touch
        amt = math.exp(-d / 0.35)
        cy = top + ch * prm.get("hit_y", 0.62)
        add_sprite(frame, G["star"], W / 2, cy, 2.6 + 1.5 * d, (1.0, 0.85, 0.55), 1.6 * amt)
        for q in range(10):
            ang = q * 0.628 + 0.3
            r = 60 + 520 * (1 - math.exp(-d / 0.25))
            add_sprite(frame, G["disc"], W / 2 + r * math.cos(ang), cy + r * math.sin(ang) * 0.7,
                       0.5 + 0.3 * (q % 3), (1.0, 0.8, 0.45), 0.9 * amt)


LAYOUTS = {"card": layout_card, "fill": layout_fill, "split": layout_split, "meet": layout_meet}

# ============================================================================ text

GOLD = (1.0, 0.80, 0.46)
WHITE = (1.0, 0.965, 0.9)


def _glyph(c, f, size, pad, w, h, anchor_xy, anchor):
    im = Image.new("L", (w, h), 0)
    ImageDraw.Draw(im).text(anchor_xy, c, font=f, fill=255, anchor=anchor)
    sharp = np.asarray(im, np.float32) / 255
    blur = np.asarray(im.filter(ImageFilter.GaussianBlur(size * 0.18)), np.float32) / 255
    shad = np.asarray(im.filter(ImageFilter.GaussianBlur(size * 0.22)), np.float32) / 255
    return sharp, blur, shad


def glyph_line(text, size, tracking=0.12, font=FONT, big=None, big_scale=1.5, big_color=None):
    """Horizontal line, baseline-aligned. `big` = substring to enlarge/colour.
    Returns (chars, width, height); chars = (dx, dy, sharp, blur, shad, colour|None)."""
    flags = [False] * len(text)
    if big and big in text:
        i0 = text.index(big)
        for k in range(i0, i0 + len(big)):
            flags[k] = True
    maxs = int(size * big_scale) if any(flags) else size
    pad = int(maxs * 0.6)
    hgt = int(maxs * 1.45) + pad * 2
    base = pad + int(maxs * 1.12)
    chars, x = [], 0.0
    for c, fl in zip(text, flags):
        sz = int(size * big_scale) if fl else size
        f = ImageFont.truetype(font, sz, index=0)
        adv = f.getlength(c)
        if c.strip() and c != "\u3000":
            sh, bl, sd = _glyph(c, f, sz, pad, int(adv) + pad * 2, hgt, (pad, base), "ls")
            chars.append((x - pad, 0, sh, bl, sd, big_color if fl else None))
        x += adv + sz * tracking
    return chars, x - size * tracking, hgt


def glyph_vertical(text, size, font=FONT, step=1.1):
    f = ImageFont.truetype(font, size, index=0)
    pad = int(size * 0.6)
    cell = size + pad * 2
    chars, y = [], 0.0
    for c in text:
        if c.strip() and c != "\u3000":
            sh, bl, sd = _glyph(c, f, size, pad, cell, cell, (cell / 2, cell / 2), "mm")
            chars.append((-cell / 2, y - pad, sh, bl, sd, None))
        y += size * step
    total = y - size * (step - 1)
    # dx already centred; report width 0 so cx is the column centre
    return [(dx, dy, a, b, c_, col) for dx, dy, a, b, c_, col in chars], 0.0, total


def draw_line(frame, glyphs, cx, cy, t_in, t_out, stagger=0.045, in_dur=0.45, rise=14,
              color=WHITE, glow=(1.0, 0.72, 0.38), glow_amt=0.45, offset=(0, 0), scatter=None):
    chars, width, height = glyphs
    col = np.array(color, np.float32)
    gcol = np.array(glow, np.float32)
    x0 = cx - width / 2 + offset[0]
    y0 = cy - height / 2 + offset[1]
    vertical = width == 0.0
    for i, (dx, dy, sharp, blur, shad, ccol) in enumerate(chars):
        a_in = ease_out((t_in - i * stagger) / in_dur)
        a = min(a_in, ease(t_out))
        if a <= 0.003:
            continue
        r = (1 - a_in) * rise
        bm = 1 - a_in
        h_, w_ = sharp.shape
        l = int(x0 + dx + (r if vertical else 0))
        tp = int(y0 + dy + (0 if vertical else r))
        if l < 0 or tp < 0 or l + w_ > W or tp + h_ > H:
            continue
        c = np.array(ccol, np.float32) if ccol is not None else col
        if scatter is not None and t_in > scatter[0]:
            # drift off screen: slow start, speeding up, turning, blurring and fading
            span = scatter[1] - scatter[0]
            u = min(1.0, max(0.0, (t_in - scatter[0] - i * 0.07) / (span * 0.85)))
            if u > 0:
                rs = np.random.default_rng(100 + i)
                ang = rs.uniform(-2.4, -0.7) if rs.random() < 0.8 else rs.uniform(-0.5, 0.5) + (math.pi if i % 2 else 0)
                dist = rs.uniform(1500, 2100)
                e2 = u * u * (3 - 2 * u) * 0.35 + u ** 2.2 * 0.65
                ox, oy = math.cos(ang) * dist * e2, math.sin(ang) * dist * e2
                rot = rs.uniform(-70, 70) * e2
                a *= 1 - ease((u - 0.55) / 0.45)
                bm = max(bm, min(1.0, u * 1.2))
                if abs(rot) > 0.5:
                    sharp = np.asarray(Image.fromarray((sharp * 255).astype(np.uint8)).rotate(rot, Image.BILINEAR), np.float32) / 255
                    blur = np.asarray(Image.fromarray((blur * 255).astype(np.uint8)).rotate(rot, Image.BILINEAR), np.float32) / 255
                    shad = blur
                cxg, cyg = l + w_ / 2, tp + h_ / 2
                for q in range(4):  # golden dust trailing the character
                    lag = 0.06 * (q + 1)
                    ul = max(0.0, u - lag)
                    el = ul * ul * (3 - 2 * ul) * 0.35 + ul ** 2.2 * 0.65
                    px = cxg + math.cos(ang + 0.25 * (q - 1.5)) * dist * el + rs.uniform(-20, 20)
                    py = cyg + math.sin(ang + 0.25 * (q - 1.5)) * dist * el + rs.uniform(-20, 20)
                    add_sprite(frame, G["disc"], px, py, 0.35 + 0.15 * (q % 2), (1.0, 0.8, 0.45), 0.7 * (1 - u) * (u > lag))
                l, tp = int(l + ox), int(tp + oy)
                if a <= 0.003:
                    continue
                # clip at the frame edge so letters slide out instead of popping
                xa, ya, xb, yb = max(0, l), max(0, tp), min(W, l + w_), min(H, tp + h_)
                if xa >= xb or ya >= yb:
                    continue
                sl = (slice(ya - tp, yb - tp), slice(xa - l, xb - l))
                sharp, blur, shad = sharp[sl], blur[sl], shad[sl]
                l, tp, h_, w_ = xa, ya, yb - ya, xb - xa
        g = sharp * (1 - bm) + blur * bm
        reg = frame[tp:tp + h_, l:l + w_]
        reg *= (1 - shad[..., None] * 0.55 * a)
        reg += blur[..., None] * gcol * glow_amt * a
        reg[:] = reg * (1 - g[..., None] * a) + c * g[..., None] * a


def parse_lyrics():
    path = os.path.join(ASSETS, "lyrics.txt")
    lines = []
    section = ""
    for raw in open(path, encoding="utf-8").read().splitlines():
        s = raw.strip()
        m = re.match(r"^(\d+):(\d+(?:\.\d+)?)(?:-(\d+):(\d+(?:\.\d+)?))?[\s　]+(.+)$", s)
        if m:
            t0 = int(m.group(1)) * 60 + float(m.group(2))
            t1 = int(m.group(3)) * 60 + float(m.group(4)) if m.group(3) else None
            lines.append([t0, t1, m.group(5).strip(), section])
        elif s:
            section = s
    for i, ln in enumerate(lines):
        nxt = lines[i + 1][0] if i + 1 < len(lines) else DURATION
        cap = 7.0 if "Chorus" in ln[3] else 5.6
        if ln[1] is None:
            ln[1] = nxt - 0.3 if ln[2] in TL.HOLD_TO_NEXT else min(nxt - 0.25, ln[0] + cap)
    return lines

# ============================================================================ frame

def shot_at(t):
    shots = G["shots"]
    i = 0
    for j, s in enumerate(shots):
        if s["t0"] <= t:
            i = j
    return i


def draw_shot(j, t):
    s = G["shots"][j]
    f = np.zeros((H, W, 3), np.float32)
    p = (t - s["t0"]) / (s["t1"] - s["t0"])
    prm = dict(s["prm"], _t0=s["t0"])
    if s["layout"] == "split":
        layout_split(f, t, p, prm, s["t1"] - s["t0"])
    else:
        LAYOUTS[s["layout"]](f, t, p, prm)
    return f


def has_rain(j):
    s = G["shots"][j]
    names = [s["prm"].get("p")] + list(s["prm"].get("ps", []))
    return any(nm in TL.RAIN for nm in names if nm)


def render_frame(n):
    t = n / FPS
    shots = G["shots"]
    i = shot_at(t)
    s = shots[i]
    # cross-dissolve centred on each cut (the fist-bump hit stays a hard cut)
    pair = None
    if i + 1 < len(shots):
        d = shots[i + 1]["xd"]
        if d and t > s["t1"] - d / 2:
            pair = (i, i + 1, ease((t - (s["t1"] - d / 2)) / d))
    if pair is None and i > 0:
        d = s["xd"]
        if d and t < s["t0"] + d / 2:
            pair = (i - 1, i, ease((t - (s["t0"] - d / 2)) / d))
    if pair:
        a_, b_, k = pair
        frame = draw_shot(a_, t) * (1 - k) + draw_shot(b_, t) * k
        rain_w = has_rain(a_) * (1 - k) + has_rain(b_) * k
    else:
        frame = draw_shot(i, t)
        rain_w = float(has_rain(i))

    # rain for outdoor shots
    if rain_w > 0.01:
        r = G["rain"]
        off = int((t * 2600) % H)
        layer = np.concatenate([r[H - off:], r[:H - off]], axis=0)
        frame += layer[..., None] * np.array([0.75, 0.82, 0.95], np.float32) * 0.22 * rain_w

    # floating warm dust
    for k, (px, py, vx, vy, sz, ph) in enumerate(G["dust"]):
        x = (px + vx * t) % (W + 100) - 50
        y = (py + vy * t + 20 * math.sin(t * 0.5 + ph)) % (H + 100) - 50
        a = 0.10 + 0.08 * math.sin(t * 1.3 + ph)
        add_sprite(frame, G["disc"], x, y, sz, (1.0, 0.78, 0.45), a)

    # impact burst where the fists meet
    if G["hit_time"] is not None and 0 <= t - G["hit_time"] < 0.9:
        d = t - G["hit_time"]
        amt = math.exp(-d / 0.3)
        bx, by = G.get("burst_xy", (W / 2, 450))
        add_sprite(frame, G["star"], bx, by, 2.4 + 1.2 * d, (1.0, 0.85, 0.55), 1.4 * amt)
        for q in range(12):
            ang = q * 0.5236 + 0.2
            rr = 50 + 480 * (1 - math.exp(-d / 0.22))
            add_sprite(frame, G["disc"], bx + rr * math.cos(ang), by + rr * math.sin(ang) * 0.7,
                       0.45 + 0.3 * (q % 3), (1.0, 0.8, 0.45), 0.9 * amt)

    # flashes on chorus downbeats + accents
    fl = 0.0
    for c in G["flash_times"]:
        dt = t - c[0]
        if 0 <= dt < 1.0:
            fl = max(fl, c[1] * math.exp(-dt / 0.14))
    if fl:
        frame = frame + (1 - frame) * fl * np.array([1.0, 0.92, 0.8], np.float32)

    frame *= G["vig"]
    frame *= G["lowband"]
    for (ta, tb, _k) in TL.TITLE_CARDS:
        if ta - 0.5 <= t <= tb + 0.5:
            k = min(ease((t - ta + 0.5) / 1.0), ease((tb + 0.5 - t) / 1.0))
            frame *= 1 - 0.5 * k * G["title_dark"]

    # global fades
    if t < 1.4:
        frame *= ease(t / 1.4)
    a, b = TL.END_FADE
    if t > a:
        frame *= 1 - ease((t - a) / (b - a))

    # titles
    for (ta, tb, _k) in TL.TITLE_CARDS:
        if ta <= t <= tb:
            out = (tb - t) / 1.0
            for glyphs, cy, dly in G["title"]:
                draw_line(frame, glyphs, W / 2, cy, t - ta - dly, out, stagger=0.09)
    # lyrics
    for L in G["lyrics"]:
        t0, t1 = L["t0"], L["t1"]
        if not (t0 - 0.05 <= t <= t1 + 0.05):
            continue
        k = min(ease((t - t0) / 0.6), ease((t1 - t) / 0.6))
        if L.get("dark"):
            frame *= 1 - L["dark"] * k * G[L.get("mask", "title_dark")]
        off = (0, 0)
        if L.get("shake"):
            d = t - t0
            amp = 16 * math.exp(-d / 0.18)
            off = (amp * math.sin(d * 61), amp * math.cos(d * 47))
        draw_line(frame, L["g"], L["cx"], L["cy"], t - t0, (t1 - t) / L.get("out", 0.45),
                  stagger=L.get("stagger", 0.045), in_dur=L.get("in", 0.45), rise=L.get("rise", 14),
                  color=L.get("color", WHITE), glow_amt=L.get("glow", 0.45), offset=off,
                  scatter=(L["scatter"][0] - t0, L["scatter"][1] - t0) if L.get("scatter") else None)

    # grain
    g = G["grain"][(n * 5) % len(G["grain"])]
    frame += g
    return (np.clip(frame, 0, 1) * 255).astype(np.uint8).tobytes()


def pace(t0, t1, n, frac, lo, hi):
    """Stagger so the characters appear across `frac` of the line's time (sung-along reveal)."""
    return min(hi, max(lo, (t1 - t0) * frac / max(1, n)))


def build_lyrics(hit):
    """Normal lines sit at the bottom and are revealed one character at a time along with the singing;
    selected lines get a lyric-video emphasis (see timeline.EMPHASIS)."""
    out = []
    lines = parse_lyrics()
    for li, (t0, t1, text, sec) in enumerate(lines):
        first = len(out)
        _lyric_entries(out, t0, t1, text, sec, hit)
        nxt = lines[li + 1][0] if li + 1 < len(lines) else None
        key = f"{int(t0 // 60)}:{int(t0 % 60):02d}"
        pat = TL.LYRIC_PATTERN.get(key, "P1")
        for e in out[first:]:
            if pat == "P0":
                continue
            e["in_dur"] = min(e.get("in_dur", 0.6), 0.35)
            end = e["t1"] + TL.EXTRA.get(pat, 0.0) if pat in TL.EXTRA else (nxt if nxt else e["t1"])
            if nxt is not None and end >= nxt:
                e["t1"], e["out"] = nxt + TL.HANDOVER, TL.HANDOVER
            else:
                e["t1"] = end
        if nxt is None and TL.SCATTER_LAST:
            for e in out[first:]:
                e["t1"] += TL.SCATTER_DELAY
                e["scatter"] = (e["t1"] - TL.EXTRA.get(pat, 0.0), e["t1"])
                e["out"] = 0.01
    return out


def _lyric_entries(out, t0, t1, text, sec, hit):
    if True:
        size = 50 if "Chorus" in sec or "Outro" in sec else 46
        em = TL.EMPHASIS.get(text)
        n = len(text.replace(" ", "").replace("\u3000", ""))
        base = dict(t0=t0, t1=t1, cx=W / 2, cy=LYRIC_Y, in_dur=0.6, rise=12, out=0.8,
                    stagger=pace(t0, t1, n, 0.62, 0.09, 0.2))
        slow = pace(t0, t1, n, 0.7, 0.12, 0.26)
        if em is None:
            out.append(dict(base, g=glyph_line(text, size)))
        elif em[0] == "word":
            out.append(dict(base, g=glyph_line(text, size, big=em[1], big_scale=1.55, big_color=GOLD)))
        elif em[0] == "side_gold":
            parts = em[1:]
            stg = pace(t0, t1, sum(len(x) for x in parts), 0.62, 0.12, 0.24)
            delay = 0.0
            for j, part in enumerate(parts):
                out.append(dict(base, t0=t0 + delay, g=glyph_line(part, 84, 0.10, FONT_B), cx=1370,
                                cy=430 + j * 125, color=GOLD, glow=0.9, stagger=stg, in_dur=0.8,
                                rise=20, dark=0.5 if j == 0 else 0.0, mask="side_dark", out=1.0))
                delay += len(part) * stg
        elif em[0] == "center":
            out.append(dict(base, g=glyph_line(text, 88, 0.10, FONT_B), cy=520, glow=0.7,
                            stagger=slow, in_dur=0.8, rise=24, dark=0.5, out=1.0))
        elif em[0] == "vertical":
            out.append(dict(base, g=glyph_vertical(text, 70, FONT_B), cx=W - 210, cy=490, glow=0.8,
                            stagger=slow, in_dur=0.9, rise=20, dark=0.55, mask="right_dark", out=1.2))
        elif em[0] == "impact":
            ht = hit if hit is not None else t0
            out.append(dict(base, t0=ht, g=glyph_line(text, 112, 0.08, FONT_B), cy=820,
                            color=GOLD, glow=1.0, stagger=0.035, in_dur=0.12, rise=0, shake=True,
                            dark=0.55, mask="low_dark", out=1.4))
        elif em[0] == "finale":
            # one character at a time, each fully placed before the next (20 % slower than before)
            out.append(dict(base, g=glyph_line(text, 84, 0.12, FONT_B), cy=520, glow=0.8,
                            stagger=0.325, in_dur=0.3, rise=18, dark=0.62, mask="all_dark", out=1.4))
    return out


def init():
    G["sprite_cache"] = {}
    G["hit_time"] = None
    G["bg_cache"] = {}
    G["flip_cache"] = {}
    G["src"], G["glints"] = load()
    G["star"] = star_sprite(120)
    G["disc"] = disc_sprite(22)
    beats = np.load(os.path.join(ASSETS, "beats.npy"))
    shots = []
    for row in TL.SHOTS:
        t0, layout, prm = row[0], row[1], row[2]
        if t0 > 0.5:
            t0 = float(beats[np.argmin(np.abs(beats - t0))])
        shots.append(dict(t0=t0, layout=layout, prm=prm, flash=(len(row) > 3)))
        if len(row) > 3 and row[3] == "hit":
            G["hit_time"] = t0
    for i, s in enumerate(shots):
        s["t1"] = shots[i + 1]["t0"] if i + 1 < len(shots) else DURATION + 0.5
    G["shots"] = shots
    for s_ in shots:
        if s_["t0"] == G["hit_time"]:
            s_["xd"] = 0.0
        elif s_["flash"]:
            s_["xd"] = 0.5
        elif s_["t0"] < 14.5 or 75.0 <= s_["t0"] < 90.0 or s_["t0"] >= 200.0:
            s_["xd"] = 1.6
        else:
            s_["xd"] = 1.2
    G["flash_times"] = [(s["t0"], 0.6 if s["t0"] == G["hit_time"] else 0.28) for s in shots if s["flash"]]
    G["flash_times"] += [(float(beats[np.argmin(np.abs(beats - t))]), a) for t, a in TL.EXTRA_FLASH]

    G["lyrics"] = build_lyrics(G["hit_time"])
    G["title"] = [(glyph_line(TL.TITLE, 96, 0.34, FONT_B), 500, 0.0),
                  (glyph_line(TL.ARTIST, 34, 0.55), 610, 0.9)]

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H / 2) / (H * 0.72)) ** 2)
    G["vig"] = np.clip(1 - 0.6 * np.clip(r - 0.45, 0, None) ** 1.5, 0, 1)[..., None].astype(np.float32)
    G["lowband"] = (1 - 0.45 * np.clip((yy[:, :1] - 880) / 160, 0, 1) ** 1.3)[..., None].astype(np.float32)
    G["side_dark"] = np.exp(-(((xx - 1370) / 520) ** 2 + ((yy - 490) / 230) ** 2))[..., None].astype(np.float32)
    G["low_dark"] = np.exp(-(((xx - W / 2) / 640) ** 2 + ((yy - 820) / 120) ** 2))[..., None].astype(np.float32)
    G["right_dark"] = (np.clip((xx[:1] - 1250) / 400, 0, 1) ** 1.2)[..., None].astype(np.float32) * np.ones((H, 1, 1), np.float32)
    G["all_dark"] = np.ones((H, W, 1), np.float32)
    G["title_dark"] = np.exp(-(((xx - W / 2) / 620) ** 2 + ((yy - 550) / 190) ** 2))[..., None].astype(np.float32)
    cg = np.exp(-(((xx - W / 2) / 380) ** 2 + ((yy - H / 2) / 420) ** 2))
    G["center_glow"] = cg[..., None].astype(np.float32)
    rng = np.random.default_rng(11)
    G["dust"] = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(-14, 14), rng.uniform(-22, -6),
                  rng.uniform(0.25, 0.9), rng.uniform(0, 6.28)) for _ in range(26)]
    grains = []
    for _ in range(10):
        sm = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
        im = Image.fromarray(np.clip(sm * 40 + 128, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
        grains.append(((np.asarray(im, np.float32) - 128) / 255 * 0.07)[..., None])
    G["grain"] = grains
    rain = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(rain)
    for _ in range(900):
        x, y = rng.uniform(-200, W), rng.uniform(0, H)
        ln = rng.uniform(30, 90)
        d.line([(x, y), (x + ln * 0.18, y + ln)], fill=int(rng.uniform(60, 200)), width=1)
    G["rain"] = np.asarray(rain.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", default="")
    ap.add_argument("--out", default=os.path.join(OUT, "africa_no_yoru_HIROSHIE.mp4"))
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    init()
    if args.stills:
        for s in args.stills.split(","):
            t = float(s)
            buf = render_frame(int(round(t * FPS)))
            Image.frombytes("RGB", (W, H), buf).save(os.path.join(OUT, f"still_{t:06.1f}.png"))
        return
    total = int(DURATION * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", os.path.join(ASSETS, "song.mp3"), "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "slow", "-b:v", "6M", "-maxrate", "8M", "-bufsize", "12M",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", args.out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(args.workers) as pool:
        for i, buf in enumerate(pool.imap(render_frame, range(total), chunksize=4)):
            enc.stdin.write(buf)
            if i % 480 == 0:
                print(f"{i}/{total}", flush=True)
    enc.stdin.close()
    enc.wait()
    print("done", args.out)


if __name__ == "__main__":
    main()
