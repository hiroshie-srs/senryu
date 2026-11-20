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
    if s % 2 == 0:
        s += 1
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
    glints = {k: find_glints(v, n=(7 if k == "Y" else 4)) for k, v in src.items()}
    return src, glints


def bg_for(name, crop):
    """Blurred, darkened cover background (slightly oversized for parallax)."""
    key = (name, crop)
    if key in G["bg_cache"]:
        return G["bg_cache"][key]
    img = G["src"][name]
    if crop:
        img = img.crop(crop)
    bw, bh = W + 120, H + 68
    sc = max(bw / img.width, bh / img.height)
    im = img.resize((int(img.width * sc) + 1, int(img.height * sc) + 1), Image.BILINEAR)
    l, t = (im.width - bw) // 2, (im.height - bh) // 2
    im = im.crop((l, t, l + bw, t + bh)).filter(ImageFilter.GaussianBlur(38))
    a = to_f(im) * 0.42 + np.array([0.02, 0.012, 0.0], np.float32)
    G["bg_cache"][key] = a
    return a

# ============================================================================ layouts

def shake(t, amp=1.0):
    return (amp * (3.0 * math.sin(t * 1.3) + 1.6 * math.sin(t * 3.7 + 1)),
            amp * (2.4 * math.sin(t * 1.7 + 2) + 1.2 * math.sin(t * 4.3)))


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
    cx = W / 2 + prm.get("dx", 0) * (e - 0.5) * 2 + sx
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
        k = ease_out((el - i * 0.07) / 0.35)
        z = 1.0 + 0.05 * p
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
    a, b = prm["ps"]
    el = t - prm["_t0"]
    k = ease_out(el / prm.get("touch", 1.5))
    bgA = bg_for(a, None)
    frame[:] = bgA[34:34 + H, 60:60 + W] * 0.8
    ch = 700
    for j, name in enumerate((a, b)):
        img = G["src"][name]
        cw = ch * img.width / img.height
        start = -cw * 0.2 if j == 0 else W - cw * 0.8
        end = W / 2 - cw - 6 if j == 0 else W / 2 + 6
        left = start + (end - start) * k
        top = H / 2 - ch / 2 - 70
        shadow(frame, left, top, cw, ch)
        place(frame, img, (0, 0, img.width, img.height), left, top, cw, ch)


LAYOUTS = {"card": layout_card, "fill": layout_fill, "split": layout_split, "meet": layout_meet}

# ============================================================================ text

def glyph_line(text, size, tracking=0.12, font=FONT):
    """Pre-render each character: returns list of (x_offset, sharp_alpha, blur_alpha) + total width."""
    f = ImageFont.truetype(font, size, index=0)
    chars = []
    x = 0.0
    pad = int(size * 0.6)
    for c in text:
        adv = f.getlength(c)
        if c.strip() and c != "　":
            im = Image.new("L", (int(adv) + pad * 2, int(size * 1.5) + pad * 2), 0)
            ImageDraw.Draw(im).text((pad, pad), c, font=f, fill=255)
            sharp = np.asarray(im, np.float32) / 255
            blur = np.asarray(im.filter(ImageFilter.GaussianBlur(size * 0.18)), np.float32) / 255
            shad = np.asarray(im.filter(ImageFilter.GaussianBlur(size * 0.22)), np.float32) / 255
            chars.append((x - pad, sharp, blur, shad))
        x += adv + size * tracking
    return chars, x - size * tracking, pad


def draw_line(frame, chars, width, pad, cx, cy, t_in, t_out, stagger=0.045, color=(1.0, 0.965, 0.9), glow=(1.0, 0.72, 0.38)):
    col = np.array(color, np.float32)
    gcol = np.array(glow, np.float32)
    x0 = cx - width / 2
    n = len(chars)
    for i, (dx, sharp, blur, shad) in enumerate(chars):
        a_in = ease_out((t_in - i * stagger) / 0.45)
        a = min(a_in, ease(t_out))
        if a <= 0.003:
            continue
        rise = (1 - a_in) * 14
        bm = 1 - a_in
        h_, w_ = sharp.shape
        l = int(x0 + dx)
        tp = int(cy - h_ / 2 + rise)
        if l < 0 or tp < 0 or l + w_ > W or tp + h_ > H:
            continue
        g = sharp * (1 - bm) + blur * bm
        reg = frame[tp:tp + h_, l:l + w_]
        reg *= (1 - shad[..., None] * 0.55 * a)
        reg += blur[..., None] * gcol * 0.45 * a
        reg[:] = reg * (1 - g[..., None] * a) + col * g[..., None] * a


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
            ln[1] = min(nxt - 0.25, ln[0] + cap)
    return lines

# ============================================================================ frame

def shot_at(t):
    shots = G["shots"]
    i = 0
    for j, s in enumerate(shots):
        if s["t0"] <= t:
            i = j
    return i


def render_frame(n):
    t = n / FPS
    frame = np.zeros((H, W, 3), np.float32)
    i = shot_at(t)
    s = G["shots"][i]
    p = (t - s["t0"]) / (s["t1"] - s["t0"])
    prm = dict(s["prm"], _t0=s["t0"])
    if s["layout"] == "split":
        layout_split(frame, t, p, prm, s["t1"] - s["t0"])
    else:
        LAYOUTS[s["layout"]](frame, t, p, prm)

    names = [s["prm"].get("p")] + list(s["prm"].get("ps", []))
    # rain for outdoor shots
    if any(nm in TL.RAIN for nm in names if nm):
        r = G["rain"]
        off = int((t * 2600) % H)
        layer = np.concatenate([r[H - off:], r[:H - off]], axis=0)
        frame += layer[..., None] * np.array([0.75, 0.82, 0.95], np.float32) * 0.22

    # floating warm dust
    for k, (px, py, vx, vy, sz, ph) in enumerate(G["dust"]):
        x = (px + vx * t) % (W + 100) - 50
        y = (py + vy * t + 20 * math.sin(t * 0.5 + ph)) % (H + 100) - 50
        a = 0.10 + 0.08 * math.sin(t * 1.3 + ph)
        add_sprite(frame, G["disc"], x, y, sz, (1.0, 0.78, 0.45), a)

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
            for (chars, width, pad), cy, dly in G["title"]:
                draw_line(frame, chars, width, pad, W / 2, cy, t - ta - dly, out, stagger=0.09)
    # lyrics
    for (t0, t1, chars, width, pad) in G["lyrics"]:
        if t0 - 0.05 <= t <= t1 + 0.05:
            draw_line(frame, chars, width, pad, W / 2, LYRIC_Y, t - t0, (t1 - t) / 0.45)

    # grain
    g = G["grain"][(n * 5) % len(G["grain"])]
    frame += g
    return (np.clip(frame, 0, 1) * 255).astype(np.uint8).tobytes()


def init():
    G["sprite_cache"] = {}
    G["bg_cache"] = {}
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
    for i, s in enumerate(shots):
        s["t1"] = shots[i + 1]["t0"] if i + 1 < len(shots) else DURATION + 0.5
    G["shots"] = shots
    G["flash_times"] = [(s["t0"], 0.6) for s in shots if s["flash"]]
    G["flash_times"] += [(float(beats[np.argmin(np.abs(beats - t))]), a) for t, a in TL.EXTRA_FLASH]

    lyr = []
    for t0, t1, text, sec in parse_lyrics():
        size = 50 if "Chorus" in sec or "Outro" in sec else 46
        chars, width, pad = glyph_line(text, size)
        lyr.append((t0, t1, chars, width, pad))
    G["lyrics"] = lyr
    G["title"] = [(glyph_line(TL.TITLE, 96, 0.34, FONT_B), 500, 0.0),
                  (glyph_line(TL.ARTIST, 34, 0.55), 610, 0.9)]

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.6)) ** 2 + ((yy - H / 2) / (H * 0.72)) ** 2)
    G["vig"] = np.clip(1 - 0.6 * np.clip(r - 0.45, 0, None) ** 1.5, 0, 1)[..., None].astype(np.float32)
    G["lowband"] = (1 - 0.45 * np.clip((yy[:, :1] - 880) / 160, 0, 1) ** 1.3)[..., None].astype(np.float32)
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
