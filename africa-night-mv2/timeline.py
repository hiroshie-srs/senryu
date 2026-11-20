# -*- coding: utf-8 -*-
"""アフリカの夜 / HIROSHIE — shot list.

Each shot: (start_sec, layout, params). A shot lasts until the next one starts.
Cut times are snapped to the song's beat grid (136 BPM) by the renderer.

layouts
  card  : one panel floating on a blurred copy of itself.  p = panel, crop=(x0,y0,x1,y1) in panel px,
          z=(zoom_start, zoom_end), dx=(px drift), dy, h=card height
  fill  : full-frame still with a Ken Burns move. a/b = (cx, cy, width) in source px
  split : 2–3 panels side by side, sliding in.  ps = [panels]
  meet  : two cards slide in from the sides and touch.  ps = [left, right]
"""

TITLE = "アフリカの夜"
ARTIST = "HIROSHIE"
END_FADE = (221.5, 227.4)

UMB = (20, 420, 300, 830)        # umbrella in the stand, panel B2
MASK_B3 = (360, 120, 508, 470)   # mask on the wall, panel B3
STOOLS = (0, 430, 508, 853)      # stools, panel B3
MASK_M1 = (420, 200, 568, 440)   # mask, panel M1
RAIN = {"B1", "B2", "C10", "Y"}

# Pacing: about one screen per lyric line (2 bars ≈ 3.5 s), longer holds in intro/interlude/outro.
# Zoom per shot is kept to ~5 % so the motion stays calm.
MOON_X = 600  # glass/moon cards sit left so the lyric can sit on the right

SHOTS = [
    # ---------------- intro
    (0.0, "fill", dict(p="Y", a=(836, 470, 1672), b=(836, 455, 1590))),
    (7.1, "card", dict(p="B1", z=(1.0, 1.04))),
    # ---------------- Verse 1
    (14.0, "card", dict(p="H3", z=(1.03, 1.0))),
    (17.0, "card", dict(p="B2", crop=UMB, z=(1.0, 1.04))),
    (21.0, "card", dict(p="H4", z=(1.0, 1.04), dx=15)),
    (24.0, "card", dict(p="H6", z=(1.04, 1.0))),
    (28.0, "card", dict(p="B1", z=(1.04, 1.0))),
    (31.5, "card", dict(p="H5", z=(1.0, 1.04))),
    # ---------------- Pre-Chorus 1
    (35.0, "card", dict(p="B2", z=(1.0, 1.05), glow=True)),
    (39.0, "card", dict(p="K10", z=(1.0, 1.04))),
    (43.0, "fill", dict(p="T1", a=(415, 232, 831), b=(415, 240, 790))),
    (46.0, "fill", dict(p="T3", a=(415, 232, 831), b=(395, 232, 790))),
    (50.0, "card", dict(p="C3", z=(1.0, 0.97))),
    # ---------------- Chorus 1
    (54.0, "fill", dict(p="TALK", a=(836, 470, 1672), b=(836, 460, 1590)), "flash"),
    (57.0, "card", dict(p="M3", z=(1.0, 1.03), x=MOON_X)),
    (61.0, "card", dict(p="H8", z=(1.0, 1.04))),
    (64.0, "fill", dict(p="Y", a=(330, 330, 760), b=(340, 335, 725))),
    (67.5, "card", dict(p="B1", z=(1.0, 1.04))),
    (71.0, "card", dict(p="H10", z=(1.04, 1.0))),
    # ---------------- interlude
    (75.6, "fill", dict(p="Y", a=(836, 470, 1672), b=(836, 470, 1590))),
    (81.0, "split", dict(ps=["C7", "H7", "M3"])),
    (85.5, "card", dict(p="H6", z=(1.0, 1.04), dark=0.25)),
    # ---------------- Verse 2
    (90.0, "fill", dict(p="T4", a=(415, 232, 831), b=(430, 240, 790))),
    (93.0, "card", dict(p="B2", crop=UMB, z=(1.04, 1.0))),
    (97.0, "card", dict(p="M2", z=(1.0, 1.04))),
    (100.0, "card", dict(p="K4", z=(1.0, 1.04))),
    (104.0, "card", dict(p="H10", z=(1.0, 1.04))),
    (107.5, "split", dict(ps=["H8", "K8", "H10"])),
    # ---------------- Pre-Chorus 2
    (111.0, "fill", dict(p="T3", a=(395, 232, 790), b=(415, 232, 831))),
    (115.0, "card", dict(p="K9", z=(1.0, 1.05), rot=(-2.0, 2.0))),
    (118.0, "card", dict(p="K8", z=(1.0, 1.04))),
    (122.0, "fill", dict(p="T2", a=(415, 232, 831), b=(430, 225, 790))),
    (125.5, "split", dict(ps=["H4", "K8", "H10"])),
    # ---------------- Chorus 2
    (129.0, "card", dict(p="H10", z=(1.0, 1.04)), "flash"),
    (131.0, "split", dict(ps=["K4", "H10", "B3"])),
    (133.0, "card", dict(p="M2", z=(1.0, 1.03), x=MOON_X)),
    (137.0, "card", dict(p="H1", z=(1.0, 1.03))),
    (140.0, "fill", dict(p="T2", a=(560, 200, 640), b=(545, 210, 672))),
    (143.5, "card", dict(p="B1", z=(1.0, 1.04))),
    (147.0, "card", dict(p="H10", z=(1.0, 1.04))),
    (151.0, "split", dict(ps=["H10", "K4", "M3"])),
    # ---------------- Bridge (the wet cat comes home — only here)
    (155.0, "card", dict(p="C9", z=(1.0, 1.04))),
    (158.0, "card", dict(p="C10", z=(1.0, 1.05))),
    (162.0, "card", dict(p="M1", crop=MASK_M1, z=(1.0, 1.04))),
    (165.0, "fill", dict(p="TALK", a=(836, 470, 1672), b=(824, 445, 1540))),
    (168.0, "fill", dict(p="FIST", a=(815, 425, 1440), b=(800, 400, 1300), burst=(792, 362)), "hit"),
    # ---------------- Chorus 3
    (175.0, "fill", dict(p="Y", a=(836, 470, 1672), b=(836, 470, 1590)), "flash"),
    (178.0, "card", dict(p="M3", z=(1.0, 1.03), x=MOON_X)),
    (182.0, "card", dict(p="H8", z=(1.0, 1.04))),
    (185.0, "fill", dict(p="T4", a=(415, 232, 831), b=(415, 232, 790))),
    (189.0, "split", dict(ps=["B1", "B2", "B3"])),
    (193.0, "card", dict(p="H10", z=(1.0, 1.04))),
    (196.5, "fill", dict(p="TALK", a=(836, 450, 1520), b=(836, 470, 1600))),
    # ---------------- Outro
    (200.0, "card", dict(p="M1", z=(1.0, 1.04))),
    (204.5, "fill", dict(p="FIST", a=(836, 470, 1672), b=(820, 440, 1560))),
    (209.6, "card", dict(p="H10", z=(1.0, 1.03))),
    (213.2, "fill", dict(p="Y", a=(836, 455, 1590), b=(836, 470, 1672))),
]

# lines that stay on screen until just before the next lyric
HOLD_TO_NEXT = {"拳が合わさる"}

# lyric-video emphasis for key lines (everything else sits small at the bottom)
EMPHASIS = {
    "グラスの底のサバンナの月": ("side_gold", "グラスの底の", "サバンナの月"),
    "俺の秋がほどけてゆく": ("vertical",),
    "俺の秋が笑ってる": ("vertical",),
    "名前も知らないラフィキと": ("word", "ラフィキ"),
    "拳が合わさる": ("impact",),
    "知らない夜がいつもの夜に": ("center",),
    "もう一杯だけ 笑わせてくれ": ("finale",),
}

# wink on the mask (bridge) and the fist-bump touch get a small flash
EXTRA_FLASH = [(163.3, 0.2)]
TITLE_CARDS = [  # (start, end, kind)
    (7.4, 13.6, "title"),
    (214.2, 222.0, "title"),
]
