# -*- coding: utf-8 -*-
"""Render the 「アフリカの夜」 lyric video.

    python3 render.py                 # full video -> out/africa_no_yoru_mv.mp4
    python3 render.py --stills 20,72  # preview frames -> out/still_XXX.png
"""
import argparse
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import ACCENTS, DURATION, LYRICS, SHOTS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
FONT = os.path.join(HERE, "fonts", "NotoSerifCJK-Regular.ttc")
OUT = os.path.join(HERE, "out")

W, H = 1920, 1080
FPS = 24
BAR = 138  # letterbox bar height (≈2.39:1)
LYRIC_Y = 742  # vertical center of lyric line
XFADE = 0.7
HARD_CUTS = {round(t, 2) for t, k in ACCENTS if k == "flash"}

# ----------------------------------------------------------------------------- grading

def _blur_np(arr, radius):
    im = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius)), dtype=np.float32) / 255.0


def grade(img, card=False):
    """Muted cinematic film look: lifted blacks, teal shadows, soft warm highlights, bloom."""
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    L = lum[..., None]
    sat = 0.80 if card else 0.74
    a = L + (a - L) * sat
    # shadows -> teal, highlights -> soft amber
    sh = (1.0 - L) ** 2
    hi = L ** 2
    a = a + sh * np.array([-0.025, 0.020, 0.045], np.float32) + hi * np.array([0.020, 0.006, -0.020], np.float32)
    a = a * np.array([0.97, 1.0, 1.03], np.float32)
    # filmic curve: lift blacks, roll off highlights
    a = np.clip(a, 0, 1)
    a = 0.055 + 0.90 * (a - 0.18 * a * a * (a - 0.4))
    if not card:
        bright = np.clip((L - 0.55) / 0.45, 0, 1) * a
        bloom = _blur_np(bright, 28)
        a = a + bloom * 0.35
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))


def make_card(path, crop=None, height=840, xc=1590):
    """Place an illustration on a 2400x1350 blue canvas with feathered edges."""
    src = Image.open(path).convert("RGB")
    if crop:
        src = src.crop(crop)
    corner = np.asarray(src, dtype=np.float32)[4:40, 4:40].reshape(-1, 3).mean(0)
    cw, ch = 2400, 1350
    canvas = np.ones((ch, cw, 3), np.float32) * corner
    rng = np.random.default_rng(7)
    canvas += rng.normal(0, 2.2, (ch, cw, 1)).astype(np.float32)  # paper texture
    scale = height / src.height
    s = src.resize((int(src.width * scale), height), Image.LANCZOS)
    sa = np.asarray(s, dtype=np.float32)
    feather = 70
    yy = np.minimum(np.arange(s.height), np.arange(s.height)[::-1])[:, None]
    xx = np.minimum(np.arange(s.width), np.arange(s.width)[::-1])[None, :]
    m = np.clip(np.minimum(yy, xx) / feather, 0, 1)[..., None]
    x0, y0 = int(xc - s.width / 2), (ch - s.height) // 2 + 20
    reg = canvas[y0:y0 + s.height, x0:x0 + s.width]
    canvas[y0:y0 + s.height, x0:x0 + s.width] = reg * (1 - m) + sa * m
    img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
    return grade(img, card=True)


def load_sources():
    src = {}
    for name in ["s1_fistbump", "s2_glass", "s3_cat", "s4_umbrella", "s5_stool"]:
        src[name] = grade(Image.open(os.path.join(ASSETS, name + ".png")))
    trip = os.path.join(ASSETS, "i_triptych.png")
    panels = [(0, 0, 720, 724), (726, 0, 1446, 724), (1452, 0, 2172, 724)]
    for i, box in enumerate(panels):
        src[f"c_trip{i}"] = make_card(trip, crop=box, height=800)
    src["c_singing"] = make_card(os.path.join(ASSETS, "i_singing.png"))
    src["c_leaning"] = make_card(os.path.join(ASSETS, "i_leaning.png"))
    src["c_thinking"] = make_card(os.path.join(ASSETS, "i_thinking.png"))
    return src

# ----------------------------------------------------------------------------- text

def render_text(text, size, tracking=0.14, color=(244, 240, 232)):
    font = ImageFont.truetype(FONT, size, index=0)
    adv = [font.getlength(c) for c in text]
    total = sum(adv) + size * tracking * (len(text) - 1)
    pad = int(size * 1.2)
    tw, th = int(total) + pad * 2, int(size * 1.6) + pad * 2
    glyph = Image.new("L", (tw, th), 0)
    d = ImageDraw.Draw(glyph)
    x = pad
    for c, a in zip(text, adv):
        d.text((x, pad), c, font=font, fill=255)
        x += a + size * tracking
    shadow = glyph.filter(ImageFilter.GaussianBlur(size * 0.18))
    g = np.asarray(glyph, np.float32) / 255.0
    s = np.asarray(shadow, np.float32) / 255.0 * 0.55
    alpha = g + s * (1 - g)
    rgb = np.zeros((th, tw, 3), np.float32)
    col = np.array(color, np.float32) / 255.0
    rgb[:] = col
    # premultiplied: glyph color over dark shadow
    pre = (g[..., None] * col)
    sharp = np.dstack([pre, alpha])
    blurred_l = glyph.filter(ImageFilter.GaussianBlur(size * 0.22))
    bg = np.asarray(blurred_l, np.float32) / 255.0
    blur = np.dstack([bg[..., None] * col, np.clip(bg * 1.1, 0, 1)])
    return sharp.astype(np.float32), blur.astype(np.float32)


def build_texts():
    texts = []
    for (t0, t1, line, style) in LYRICS:
        size = 46 if style == "s" else 40
        sharp, blur = render_text(line, size)
        texts.append((t0, t1, sharp, blur))
    return texts


def comp_text(frame, sharp, blur, cx, cy, alpha, blur_mix):
    th, tw = sharp.shape[:2]
    x0, y0 = int(cx - tw / 2), int(cy - th / 2)
    tex = sharp * (1 - blur_mix) + blur * blur_mix
    pre, a = tex[..., :3], tex[..., 3:4] * alpha
    reg = frame[y0:y0 + th, x0:x0 + tw]
    frame[y0:y0 + th, x0:x0 + tw] = reg * (1 - a) + pre * alpha

# ----------------------------------------------------------------------------- per-frame

G = {}


def ease(p):
    p = min(max(p, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * p)


def camera(img, a, b, p):
    e = 0.15 * p + 0.85 * ease(p)  # gentle ease with constant drift
    cx = a[0] + (b[0] - a[0]) * e
    cy = a[1] + (b[1] - a[1]) * e
    w = a[2] + (b[2] - a[2]) * e
    iw, ih = img.size
    w = min(w, iw, ih * 16 / 9)
    h = w * 9 / 16
    cx = min(max(cx, w / 2), iw - w / 2)
    cy = min(max(cy, h / 2), ih - h / 2)
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    out = img.transform((W, H), Image.EXTENT, box, Image.BICUBIC)
    return np.asarray(out, np.float32) / 255.0


def shot_frame(i, t):
    s0, s1, name, a, b = SHOTS[i]
    p = (t - s0) / (s1 - s0)
    return camera(G["src"][name], a, b, p)


def picture(t):
    shots = SHOTS
    idx = max(i for i, s in enumerate(shots) if s[0] <= t or i == 0)
    frame = shot_frame(idx, t)
    # crossfade into the next shot around the cut
    if idx + 1 < len(shots):
        cut = shots[idx][1]
        xf = 0.0 if round(cut, 2) in HARD_CUTS else XFADE
        if xf and t > cut - xf / 2:
            k = ease((t - (cut - xf / 2)) / xf)
            frame = frame * (1 - k) + shot_frame(idx + 1, t) * k
    if idx > 0:
        cut = shots[idx][0]
        xf = 0.0 if round(cut, 2) in HARD_CUTS else XFADE
        if xf and t < cut + xf / 2:
            k = ease((t - (cut - xf / 2)) / xf)
            frame = shot_frame(idx - 1, t) * (1 - k) + frame * k
    return frame


def render_frame(n):
    t = n / FPS
    f = picture(t)

    # accents
    for t0, kind in ACCENTS:
        dt = t - t0
        if 0 <= dt < 1.2:
            if kind == "flash":
                f = f + (1 - f) * 0.55 * math.exp(-dt / 0.16)
            elif kind == "flash_small":
                f = f + (1 - f) * 0.30 * math.exp(-dt / 0.10)
            elif kind == "wink":
                f = f * (1 + 0.45 * math.exp(-dt / 0.09))
        elif kind == "flash" and -0.35 < dt < 0:  # tiny dip before the drop
            f = f * (1 - 0.35 * (1 + dt / 0.35))

    # subtle lamp breathing
    f = f * (1 + 0.012 * math.sin(t * 2.1) + 0.006 * math.sin(t * 7.3))

    f = f * G["vig"]

    # global fades
    if t < 1.6:
        f = f * ease(t / 1.6)
    if t > 209.4:
        f = f * (1 - ease((t - 209.4) / 1.4))

    # title cards
    for (ta, tb, tex, cy) in G["titles"]:
        if ta - 0.01 <= t <= tb:
            fin = ease((t - ta) / 1.4)
            fout = 1 - ease((t - (tb - 1.2)) / 1.2)
            al = min(fin, fout)
            comp_text(f, tex[0], tex[1], W / 2, cy, al, 1 - al)

    # lyrics (shifted left on illustration cards so they clear the figure)
    cur = max(i for i, s in enumerate(SHOTS) if s[0] <= t or i == 0)
    lx = 720 if SHOTS[cur][2].startswith("c_") else W / 2
    for (t0, t1, sharp, blur) in G["texts"]:
        if t0 <= t <= t1 + 0.05:
            fin = (t - t0) / 0.65
            fout = (t1 - t) / 0.5
            al = ease(min(fin, fout, 1.0))
            bm = 1 - ease(min(fin, 1.0)) if fin < fout else 1 - ease(min(fout, 1.0)) * 1.0
            rise = (1 - ease(min(fin, 1.0))) * 10
            comp_text(f, sharp, blur, lx, LYRIC_Y + rise, al, bm * 0.9)

    # grain
    g = G["grain"][(n * 7) % len(G["grain"])]
    f = f + g * (0.55 + 0.45 * (1 - f.mean(axis=2, keepdims=True)))

    f[:BAR] = 0
    f[H - BAR:] = 0
    return (np.clip(f, 0, 1) * 255).astype(np.uint8).tobytes()


def init_globals():
    G["src"] = load_sources()
    G["texts"] = build_texts()
    title = render_text("アフリカの夜", 78, tracking=0.38)
    artist = render_text("ヒロシエ", 30, tracking=0.6)
    end1 = render_text("アフリカの夜", 56, tracking=0.38)
    end2 = render_text("ヒロシエ", 26, tracking=0.6)
    G["titles"] = [
        (2.2, 12.6, title, 520), (3.4, 12.6, artist, 610),
        (209.9, 212.1, end1, 520), (210.3, 212.1, end2, 595),
    ]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2)
    G["vig"] = np.clip(1 - 0.55 * np.clip(r - 0.35, 0, None) ** 1.6, 0, 1)[..., None].astype(np.float32)
    rng = np.random.default_rng(3)
    grains = []
    for _ in range(12):
        small = rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
        im = Image.fromarray(np.clip(small * 40 + 128, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
        grains.append(((np.asarray(im, np.float32) - 128) / 255.0 * 0.11)[..., None])
    G["grain"] = grains


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", default="")
    ap.add_argument("--out", default=os.path.join(OUT, "africa_no_yoru_mv.mp4"))
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    init_globals()

    if args.stills:
        for s in args.stills.split(","):
            t = float(s)
            buf = render_frame(int(round(t * FPS)))
            Image.frombytes("RGB", (W, H), buf).save(os.path.join(OUT, f"still_{t:06.1f}.png"))
        return

    total = int(math.ceil(DURATION * FPS))
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", os.path.join(ASSETS, "song.mp3"),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-tune", "grain", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart",
        args.out,
    ]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(args.workers) as pool:
        for i, buf in enumerate(pool.imap(render_frame, range(total), chunksize=4)):
            enc.stdin.write(buf)
            if i % 240 == 0:
                print(f"{i}/{total}", flush=True)
    enc.stdin.close()
    enc.wait()
    print("done", args.out)


if __name__ == "__main__":
    main()
