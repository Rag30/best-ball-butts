"""Brief extras, run from the run dir after src_agg.py: the weekly points chart and the toilet bowl table.

Writes
  weekly_points.svg  one line per manager: best-ball points in each finished week (m26_w<w>.json, weeks < START).
                     Self-contained SVG (no scripts, no fonts to fetch), so the PDF and the site both show it as an image.
  toilet.md          markdown table: each manager's chance of finishing 8th (losing the Week 15 7-vs-8 game, which is
                     this league's whole losers bracket), this edition's consensus plus the last few editions' values
                     from runs/*/agg.json, so the trend reads week over week.
usage: python3 <pipeline>/brief_extras.py
"""
import sys as _s, os as _o; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
import json, os, math
from wk import START

M = ["Conrad", "Lauren", "Emma", "Raghav", "Avery", "Ben", "Noelle", "Henry"]  # roster_id order: color follows the manager
# Categorical palette in fixed order (dataviz reference palette, validated: adjacent CVD dE >= 9.1 on light surface).
COL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, GRID, SURF = "#1a201c", "#5b645e", "#e4e8e5", "#ffffff"

# ---------------- weekly points chart ----------------
rost = json.load(open("rostered_players.json"))
rid = {v["manager"]: v["roster_id"] for v in rost.values()}
weeks = [w for w in range(1, START) if os.path.isfile(f"m26_w{w}.json")]
pts = {m: [] for m in M}
for w in weeks:
    by = {e["roster_id"]: e["points"] for e in json.load(open(f"m26_w{w}.json"))}
    for m in M: pts[m].append(float(by.get(rid[m], 0) or 0))

Wd, Ht = 720, 300
L_, R_, T_, B_ = 40, 92, 34, 28          # plot margins: right side holds the direct labels
pw, ph = Wd - L_ - R_, Ht - T_ - B_
allv = [v for m in M for v in pts[m]] or [0, 1]
lo = 20 * math.floor(min(allv) / 20); hi = 20 * math.ceil(max(allv) / 20)
if hi == lo: hi = lo + 20
X = lambda i: L_ + (pw * i / (len(weeks) - 1) if len(weeks) > 1 else pw / 2)
Y = lambda v: T_ + ph * (1 - (v - lo) / (hi - lo))
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wd} {Ht}" width="{Wd}" height="{Ht}" '
     f'font-family="Helvetica,Arial,sans-serif" role="img" aria-label="Points scored each week by each manager, Weeks 1 to {weeks[-1] if weeks else 0}">',
     f'<rect width="{Wd}" height="{Ht}" fill="{SURF}"/>']
# legend (always present for >= 2 series): one row across the top, swatch + name in ink
lx = L_
for k, m in enumerate(M):
    o.append(f'<line x1="{lx}" y1="13" x2="{lx+14}" y2="13" stroke="{COL[k]}" stroke-width="3" stroke-dasharray="0.1 4.6" stroke-linecap="round"/>'
             f'<text x="{lx+18}" y="17" font-size="11" fill="{INK}">{m}</text>')
    lx += 18 + 7 * len(m) + 16
# recessive grid + axes
step = 20 if hi - lo <= 160 else 40
for v in range(int(lo), int(hi) + 1, step):
    o.append(f'<line x1="{L_}" y1="{Y(v):.1f}" x2="{L_+pw}" y2="{Y(v):.1f}" stroke="{GRID}" stroke-width="1"/>'
             f'<text x="{L_-6}" y="{Y(v)+3.5:.1f}" font-size="10" fill="{INK2}" text-anchor="end">{v}</text>')
for i, w in enumerate(weeks):
    o.append(f'<text x="{X(i):.1f}" y="{T_+ph+15}" font-size="10" fill="{INK2}" text-anchor="middle">W{w}</text>')
o.append(f'<text x="{L_+pw/2:.1f}" y="{Ht-2}" font-size="10" fill="{INK2}" text-anchor="middle">Points by week: best-ball score in each finished week</text>')
# lines: dotted (round-capped dashes), small ringed markers, a native tooltip on each point
for k, m in enumerate(M):
    p = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(pts[m]))
    o.append(f'<polyline points="{p}" fill="none" stroke="{COL[k]}" stroke-width="2.4" stroke-dasharray="0.1 4.6" stroke-linejoin="round" stroke-linecap="round"/>')
    for i, v in enumerate(pts[m]):
        o.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3" fill="{COL[k]}" stroke="{SURF}" stroke-width="1.5">'
                 f'<title>{m}, Week {weeks[i]}: {v:.1f}</title></circle>')
# the manager's name written along their own line at intervals: on the flattest segments, spread out, and placed
# so no two names sit on top of each other (greedy, flattest first). White halo keeps the name readable over other lines.
taken = []; per = {m: [] for m in M}
cands = []
for k, m in enumerate(M):
    for i in range(len(weeks) - 1):
        x0, y0, x1, y1 = X(i), Y(pts[m][i]), X(i + 1), Y(pts[m][i + 1])
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        if abs(ang) <= 40: cands.append((abs(ang), k, m, i, (x0 + x1) / 2, (y0 + y1) / 2, ang))
for a_, k, m, i, cx, cy, ang in sorted(cands):
    if len(per[m]) >= 3 or any(abs(i - j) < 3 for j in per[m]): continue
    w2 = 3.2 * len(m) + 4
    if any(abs(cx - tx) < w2 + tw and abs(cy - ty) < 11 for tx, ty, tw in taken): continue
    taken.append((cx, cy, w2)); per[m].append(i)
    o.append(f'<text x="{cx:.1f}" y="{cy:.1f}" transform="rotate({ang:.1f} {cx:.1f} {cy:.1f})" dy="3.5" font-size="9.5" font-weight="700" '
             f'text-anchor="middle" fill="{COL[k]}" stroke="{SURF}" stroke-width="3" paint-order="stroke" stroke-linejoin="round">{m}</text>')
# direct labels at the last point, nudged apart so none overlap (min 12px)
if weeks:
    lab = sorted(((Y(pts[m][-1]), m, k) for k, m in enumerate(M)))
    ys = [y for y, _, _ in lab]
    for _ in range(50):
        for j in range(1, len(ys)):
            if ys[j] - ys[j-1] < 12: d = (12 - (ys[j] - ys[j-1])) / 2; ys[j-1] -= d; ys[j] += d
    for (y0, m, k), y in zip(lab, ys):
        x = X(len(weeks) - 1)
        o.append(f'<line x1="{x+4:.1f}" y1="{y0:.1f}" x2="{x+12:.1f}" y2="{y:.1f}" stroke="{COL[k]}" stroke-width="1"/>'
                 f'<text x="{x+15:.1f}" y="{y+3.5:.1f}" font-size="10" fill="{INK}">{m} {pts[m][-1]:.0f}</text>')
o.append("</svg>")
open("weekly_points.svg", "w").write("\n".join(o) + "\n")
print(f"wrote weekly_points.svg: weeks {weeks[0] if weeks else '-'}-{weeks[-1] if weeks else '-'}")

# ---------------- toilet bowl table ----------------
if os.path.isfile("agg.json"):
    here = os.path.abspath(".")
    hist = []   # (week start, consensus) for earlier editions, newest edition per week
    for d in sorted(os.listdir("..")):
        p = os.path.join("..", d)
        if os.path.abspath(p) == here or not (os.path.isfile(os.path.join(p, "agg.json")) and os.path.isfile(os.path.join(p, "week.json"))): continue
        hist.append((json.load(open(os.path.join(p, "week.json")))["start"], json.load(open(os.path.join(p, "agg.json")))["consensus"]))
    byweek = {}
    for w, c in hist:
        if w < START: byweek[w] = c   # later folders win within a week
    prev = sorted(byweek)[-3:]
    cons = json.load(open("agg.json"))["consensus"]
    last = lambda c, m: c[m]["finish"]["8"] if isinstance(c[m]["finish"], dict) and "8" in c[m]["finish"] else c[m]["finish"][8]
    f = lambda v: "<0.1" if v < 0.05 else f"{v:.1f}"
    rows = sorted(M, key=lambda m: (-last(cons, m), -cons[m]["xw"]))
    t = ["| # | Manager | Rec | Toilet bowl % | 7–8 game % | " + " | ".join(f"Wk {w} ed." for w in prev) + " | Δ |",
         "|---|---|:-:|--:|--:|" + "--:|" * len(prev) + "--:|"]
    for i, m in enumerate(rows):
        now = last(cons, m); old = [last(byweek[w], m) for w in prev]
        miss = 100 - cons[m]["playoff"]
        d = f"{now-old[-1]:+.1f}".replace("-", "−") if old else "–"
        t.append(f"| {i+1} | {'**'+m+'**' if i == 0 else m} | {cons[m]['rec']} | {'**'+f(now)+'**' if i == 0 else f(now)} | {f(miss)} | "
                 + " | ".join(f(v) for v in old) + f" | {d} |")
    open("toilet.md", "w").write("\n".join(t) + "\n")
    print("wrote toilet.md\n" + "\n".join(t))
else:
    print("no agg.json yet: run src_agg.py first for toilet.md")
