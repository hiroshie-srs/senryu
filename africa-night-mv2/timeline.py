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

SHOTS = [
    # ---------------- intro
    (0.0, "fill", dict(p="Y", a=(836, 470, 1672), b=(836, 440, 1450))),
    (3.6, "fill", dict(p="Y", a=(1300, 330, 900), b=(1240, 360, 1000))),
    (7.1, "card", dict(p="B1", z=(1.0, 1.10), dy=-20)),
    # ---------------- Verse 1
    (14.0, "card", dict(p="H3", z=(1.04, 1.0))),
    (15.8, "card", dict(p="B1", crop=(0, 380, 567, 853), z=(1.0, 1.08))),
    (17.0, "card", dict(p="B2", crop=UMB, z=(1.0, 1.12))),
    (19.2, "card", dict(p="B2", z=(1.08, 1.0))),
    (21.0, "card", dict(p="H4", z=(1.0, 1.08), dx=20)),
    (22.8, "card", dict(p="H2", z=(1.0, 1.05), dx=-30)),
    (24.0, "card", dict(p="H6", z=(1.06, 1.0))),
    (25.9, "card", dict(p="H1", z=(1.0, 1.06), dark=0.35)),
    (28.0, "card", dict(p="B1", z=(1.12, 1.0))),
    (31.5, "card", dict(p="H5", z=(1.0, 1.06), dx=-25)),
    # ---------------- Pre-Chorus 1
    (35.0, "card", dict(p="B2", z=(1.0, 1.25), dy=30, glow=True)),
    (39.0, "card", dict(p="B3", crop=MASK_B3, z=(1.0, 1.08))),
    (40.8, "card", dict(p="K10", z=(1.0, 1.08))),
    (43.0, "fill", dict(p="T1", a=(415, 232, 831), b=(430, 250, 700))),
    (46.0, "fill", dict(p="T3", a=(415, 232, 831), b=(330, 230, 690))),
    (48.0, "card", dict(p="C3", z=(1.0, 0.94))),
    (50.0, "card", dict(p="H4", z=(1.0, 1.06))),
    (52.2, "card", dict(p="H5", z=(1.06, 1.0))),
    # ---------------- Chorus 1
    (54.0, "fill", dict(p="TALK", a=(836, 470, 1672), b=(836, 440, 1450)), "flash"),
    (55.8, "split", dict(ps=["H10", "K4", "B3"])),
    (57.0, "card", dict(p="M2", z=(1.0, 1.15), dy=-10)),
    (58.8, "card", dict(p="M3", z=(1.0, 1.10))),
    (61.0, "card", dict(p="H8", z=(1.0, 1.08))),
    (62.6, "card", dict(p="H4", z=(1.06, 1.0))),
    (64.0, "fill", dict(p="Y", a=(330, 330, 760), b=(380, 360, 660))),
    (65.8, "card", dict(p="B1", z=(1.0, 1.06))),
    (67.5, "split", dict(ps=["H1", "C1", "H3"])),
    (69.3, "card", dict(p="H5", z=(1.0, 1.06))),
    (71.0, "card", dict(p="H10", z=(1.06, 1.0))),
    (73.5, "card", dict(p="H1", z=(1.0, 1.05))),
    # ---------------- interlude
    (75.6, "fill", dict(p="Y", a=(836, 470, 1672), b=(836, 470, 1400))),
    (79.1, "split", dict(ps=["C7", "H7", "M3"])),
    (81.7, "card", dict(p="M1", z=(1.0, 1.08))),
    (84.3, "card", dict(p="C10", z=(1.0, 1.08))),
    (86.9, "card", dict(p="H6", z=(1.0, 1.05), dark=0.25)),
    # ---------------- Verse 2
    (90.0, "fill", dict(p="T4", a=(415, 232, 831), b=(470, 260, 680))),
    (91.8, "card", dict(p="M1", crop=MASK_M1, z=(1.0, 1.10))),
    (93.0, "card", dict(p="B2", crop=UMB, z=(1.10, 1.0))),
    (95.0, "card", dict(p="B2", z=(1.0, 1.05))),
    (97.0, "card", dict(p="M2", z=(1.0, 1.10))),
    (100.0, "card", dict(p="K4", z=(1.0, 1.06))),
    (102.0, "card", dict(p="H8", z=(1.0, 1.08))),
    (104.0, "card", dict(p="H10", z=(1.0, 1.05))),
    (106.0, "split", dict(ps=["H8", "K8", "H10"])),
    (108.0, "card", dict(p="H1", z=(1.04, 1.0))),
    # ---------------- Pre-Chorus 2
    (111.0, "fill", dict(p="T3", a=(330, 230, 690), b=(415, 232, 831))),
    (113.0, "card", dict(p="K5", z=(1.0, 1.06))),
    (115.0, "card", dict(p="K9", z=(1.0, 1.14), rot=(-3.0, 3.0))),
    (118.0, "card", dict(p="K8", z=(1.0, 1.06))),
    (120.0, "card", dict(p="B3", z=(1.06, 1.0))),
    (122.0, "fill", dict(p="T2", a=(415, 232, 831), b=(520, 210, 680))),
    (124.0, "card", dict(p="K4", z=(1.0, 1.05))),
    (126.2, "split", dict(ps=["H4", "K8", "H10"])),
    # ---------------- Chorus 2
    (129.0, "card", dict(p="H10", z=(1.0, 1.06)), "flash"),
    (131.0, "split", dict(ps=["K4", "H10", "B3"])),
    (133.0, "card", dict(p="M3", z=(1.0, 1.12))),
    (135.0, "card", dict(p="M2", z=(1.08, 1.0))),
    (137.0, "card", dict(p="H1", z=(1.0, 1.02))),
    (137.9, "card", dict(p="K2", z=(1.0, 1.02))),
    (138.8, "card", dict(p="H3", z=(1.0, 1.02))),
    (139.3, "card", dict(p="K3", z=(1.0, 1.02))),
    (140.0, "fill", dict(p="T2", a=(560, 200, 640), b=(415, 232, 831))),
    (142.0, "fill", dict(p="Y", a=(330, 330, 760), b=(300, 300, 680))),
    (144.0, "card", dict(p="B1", z=(1.0, 1.08))),
    (147.0, "card", dict(p="H10", z=(1.0, 1.06))),
    (150.0, "split", dict(ps=["H10", "K4", "M3"])),
    (152.0, "card", dict(p="H5", z=(1.0, 1.05))),
    # ---------------- Bridge
    (155.0, "card", dict(p="C9", z=(1.0, 1.10))),
    (158.0, "card", dict(p="C10", z=(1.0, 1.08))),
    (160.0, "card", dict(p="C1", z=(1.04, 1.0))),
    (162.0, "card", dict(p="M1", crop=MASK_M1, z=(1.0, 1.12))),
    (165.0, "fill", dict(p="TALK", a=(836, 470, 1672), b=(820, 420, 1400))),
    (166.5, "fill", dict(p="FIST", a=(820, 420, 1400), b=(795, 375, 760), burst=(792, 362)), "hit"),
    (169.6, "split", dict(ps=["H10", "K8"])),
    (171.2, "card", dict(p="K10", z=(1.0, 1.06))),
    (172.6, "card", dict(p="H10", z=(1.0, 1.04))),
    # ---------------- Chorus 3
    (175.0, "fill", dict(p="Y", a=(836, 470, 1672), b=(836, 470, 1500)), "flash"),
    (177.0, "fill", dict(p="T4", a=(415, 232, 831), b=(415, 232, 700))),
    (178.0, "card", dict(p="M2", z=(1.0, 1.12))),
    (180.0, "card", dict(p="M3", z=(1.0, 1.12))),
    (182.0, "card", dict(p="H8", z=(1.0, 1.08))),
    (183.6, "card", dict(p="C5", z=(1.0, 1.06))),
    (185.0, "card", dict(p="B1", z=(1.0, 1.06))),
    (187.0, "split", dict(ps=["B1", "B2", "B3"])),
    (189.0, "card", dict(p="H4", z=(1.0, 1.06))),
    (191.0, "card", dict(p="H6", z=(1.0, 1.04))),
    (193.0, "card", dict(p="H10", z=(1.0, 1.06))),
    (196.0, "split", dict(ps=["H10", "K4", "C1"])),
    (198.0, "fill", dict(p="TALK", a=(836, 420, 1250), b=(836, 470, 1672))),
    # ---------------- Outro
    (200.0, "card", dict(p="M1", z=(1.0, 1.10))),
    (202.6, "card", dict(p="M3", z=(1.0, 1.25))),
    (206.1, "fill", dict(p="FIST", a=(836, 470, 1672), b=(800, 400, 1200))),
    (209.6, "card", dict(p="H10", z=(1.0, 1.06))),
    (213.2, "fill", dict(p="Y", a=(836, 420, 1250), b=(836, 470, 1672))),
]

# lyric-video emphasis for key lines (everything else sits small at the bottom)
EMPHASIS = {
    "グラスの底のサバンナの月": ("center_gold",),
    "俺の秋がほどけてゆく": ("vertical",),
    "俺の秋が笑ってる": ("vertical",),
    "名前も知らないラフィキと": ("word", "ラフィキ"),
    "カウンター越しに拳が合わさる": ("impact", "拳が合わさる"),
    "知らない夜がいつもの夜に": ("center",),
    "もう一杯だけ 笑わせてくれ": ("finale",),
}

# wink on the mask (bridge) and the fist-bump touch get a small flash
EXTRA_FLASH = [(163.3, 0.35)]
TITLE_CARDS = [  # (start, end, kind)
    (7.4, 13.6, "title"),
    (214.2, 222.0, "title"),
]
