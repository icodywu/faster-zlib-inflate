"""Draw images/speed-light.svg and images/speed-dark.svg (level 6, one call and 16K/64K pieces) from
results/speed_epyc9334.txt, best round, -O2.

usage: python3 images/make_charts.py
"""
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
best = defaultdict(float)
for line in open(os.path.join(HERE, "..", "results", "speed_epyc9334.txt")):
    if line.startswith("#"):
        continue
    f = dict(kv.split("=", 1) for kv in line.split())
    if f["cflags"] != "-O2" or f["level"] != "6":
        continue
    k = (f["corpus"], f["build"], f["mode"])
    best[k] = max(best[k], float(f["MB/s"]))

CORPORA = [("silesia", "Silesia"), ("canterbury+calgary", "Canterbury + Calgary"), ("enwik8", "enwik8")]
PANELS = [("one-call", "One inflate() call"), ("16K/64K", "16 KiB in / 64 KiB out")]
THEMES = {
    "light": dict(bg="#ffffff", ink="#1f2328", muted="#59636e", rule="#d1d9e0", stock="#a3aeb8", new="#0c6f6c"),
    "dark": dict(bg="#0d1117", ink="#e6edf3", muted="#9198a1", rule="#3d444d", stock="#5d6a76", new="#45bdb4"),
}
W, PANEL_W, LEFT, MAXV = 880, 400, 150, 1000
BAR, GAP_GROUP = 14, 16


def svg(theme):
    t = THEMES[theme]
    rows_h = len(CORPORA) * (2 * BAR + 4 + GAP_GROUP)
    H = 64 + rows_h + 40
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
           'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">' % (W, H, W, H),
           '<rect width="100%%" height="100%%" fill="%s"/>' % t["bg"]]
    # legend
    out.append('<rect x="20" y="16" width="12" height="12" rx="2" fill="%s"/>' % t["stock"])
    out.append('<text x="38" y="27" font-size="13" fill="%s">zlib develop</text>' % t["muted"])
    out.append('<rect x="140" y="16" width="12" height="12" rx="2" fill="%s"/>' % t["new"])
    out.append('<text x="158" y="27" font-size="13" fill="%s">patched</text>' % t["muted"])
    out.append('<text x="%d" y="27" font-size="12" fill="%s" text-anchor="end">MB/s, zlib level 6, AMD EPYC 9334, one core, GCC 14.2 -O2</text>'
               % (W - 20, t["muted"]))
    for p, (mode, title) in enumerate(PANELS):
        x0 = 20 + p * (PANEL_W + 40)
        scale = (PANEL_W - LEFT - 46) / MAXV
        out.append('<text x="%d" y="56" font-size="13" font-weight="600" fill="%s">%s</text>' % (x0, t["ink"], title))
        y = 70
        for key, label in CORPORA:
            out.append('<text x="%d" y="%d" font-size="12" fill="%s">%s</text>' % (x0, y + BAR + 2, t["ink"], label))
            for i, (b, color) in enumerate((("stock", t["stock"]), ("patched", t["new"]))):
                v = best[(key, b, mode)]
                yy = y + i * (BAR + 4)
                out.append('<rect x="%d" y="%d" width="%.1f" height="%d" fill="%s"/>' % (x0 + LEFT, yy, v * scale, BAR, color))
                weight = ' font-weight="600"' if b == "patched" else ""
                out.append('<text x="%.1f" y="%d" font-size="11" fill="%s"%s>%.0f</text>'
                           % (x0 + LEFT + v * scale + 5, yy + BAR - 3, t["ink"] if b == "patched" else t["muted"], weight, v))
            gain = best[(key, "patched", mode)] / best[(key, "stock", mode)] - 1
            out.append('<text x="%d" y="%d" font-size="11" fill="%s">+%.0f%%</text>' % (x0, y + 2 * BAR + 14, t["new"], gain * 100))
            y += 2 * BAR + 4 + GAP_GROUP
        # axis
        out.append('<line x1="%d" y1="%d" x2="%.1f" y2="%d" stroke="%s"/>' % (x0 + LEFT, y, x0 + LEFT + MAXV * scale, y, t["rule"]))
        for v in range(0, MAXV + 1, 200):
            out.append('<text x="%.1f" y="%d" font-size="10" fill="%s" text-anchor="middle">%d</text>'
                       % (x0 + LEFT + v * scale, y + 14, t["muted"], v))
    out.append("</svg>")
    return "\n".join(out) + "\n"


for theme in THEMES:
    with open(os.path.join(HERE, "speed-%s.svg" % theme), "w", newline="\n") as f:
        f.write(svg(theme))
print("wrote images/speed-light.svg and images/speed-dark.svg")
