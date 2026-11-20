# -*- coding: utf-8 -*-
"""Cut the numbered panels out of the reference sheets and paint out the number badges."""
import os
import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SHEETS = os.path.join(HERE, "assets", "sheets")
OUT = os.path.join(HERE, "assets", "panels")

H_TOP = [(8, 336), (346, 666), (676, 995), (1005, 1326), (1336, 1664)]
H_BOT = [(8, 329), (339, 665), (675, 979), (990, 1280), (1290, 1665)]
C_TOP = [(10, 288), (296, 738), (746, 985), (993, 1321), (1330, 1662)]
C_BOT = [(10, 322), (332, 658), (668, 965), (976, 1271), (1280, 1662)]
SPEC = {
    "hiroshie": [(x, 63, y, 484) for x, y in H_TOP] + [(x, 494, y, 926) for x, y in H_BOT],
    "cat": [(x, 80, y, 467) for x, y in C_TOP] + [(x, 480, y, 911) for x, y in C_BOT],
    "bar": [(11, 63, 578, 916), (594, 63, 1136, 916), (1152, 63, 1662, 916)],
    "moon": [(11, 63, 579, 916), (595, 63, 1134, 916), (1150, 63, 1661, 916)],
}
PREFIX = {"hiroshie": "H", "cat": "C", "bar": "B", "moon": "M"}
BADGE = {"hiroshie": 58, "cat": 46, "bar": 66, "moon": 66}

os.makedirs(OUT, exist_ok=True)
for sheet, boxes in SPEC.items():
    img = cv2.imread(os.path.join(SHEETS, sheet + ".webp"))
    for i, (x0, y0, x1, y1) in enumerate(boxes, 1):
        p = img[y0 + 2:y1 - 1, x0 + 2:x1 - 1].copy()
        b = BADGE[sheet]
        mask = np.zeros(p.shape[:2], np.uint8)
        corner = cv2.cvtColor(p[:b, :b], cv2.COLOR_BGR2GRAY)
        # badge = bright plate + its dark outline/digits; take the whole corner block where it differs from bg
        mask[:b, :b] = 255
        res = cv2.inpaint(p, mask, 9, cv2.INPAINT_TELEA)
        # soften the patched corner a little
        blur = cv2.GaussianBlur(res, (0, 0), 6)
        m = np.zeros(p.shape[:2], np.float32)
        m[:b + 8, :b + 8] = 1
        m = cv2.GaussianBlur(m, (0, 0), 6)[..., None]
        res = (res * (1 - m) + blur * m).astype(np.uint8)
        cv2.imwrite(os.path.join(OUT, f"{PREFIX[sheet]}{i}.png"), res)
print("ok")
