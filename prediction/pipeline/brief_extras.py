"""Brief extras, run from the run dir after src_agg.py: the weekly points chart, the toilet bowl table and its trend chart.

Writes
  weekly_points.svg  one line per manager: best-ball points in each finished week (m26_w<w>.json, weeks < START).
                     Self-contained SVG (no scripts, no fonts to fetch), so the PDF and the site both show it as an image.
  toilet.md          markdown table: each manager's chance of finishing 8th (losing the Week 15 7-vs-8 game, which is
                     this league's whole losers bracket), this edition's consensus plus the last few editions' values
                     from runs/*/agg.json, so the trend reads week over week.
  toilet_trend.svg   the same chance of finishing last as a chart: one dotted line per manager across every edition.
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

def endv(v, unit):
    return "&lt;1" if unit == "%" and 0 < v < 0.5 else f"{v:.0f}"


def line_chart(fname, xlab, ser, step, unit, aria, caption, tip):
    """One dotted line per manager over xlab (axis labels), names written along the lines, end labels with the last value.
    ser: {manager: [value per x]}; step: y gridline step; unit: suffix on axis/end labels; tip: x label used in tooltips."""
    weeks = xlab; pts = ser
    Wd, Ht = 720, 300
    L_, R_, T_, B_ = 40, 92, 34, 28          # plot margins: right side holds the direct labels
    pw, ph = Wd - L_ - R_, Ht - T_ - B_
    allv = [v for m in M for v in pts[m]] or [0, 1]
    lo = step * math.floor(min(allv) / step); hi = step * math.ceil(max(allv) / step)
    if hi == lo: hi = lo + step
    X = lambda i: L_ + (pw * i / (len(weeks) - 1) if len(weeks) > 1 else pw / 2)
    Y = lambda v: T_ + ph * (1 - (v - lo) / (hi - lo))
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wd} {Ht}" width="{Wd}" height="{Ht}" '
         f'font-family="Helvetica,Arial,sans-serif" role="img" aria-label="{aria}">',
         f'<rect width="{Wd}" height="{Ht}" fill="{SURF}"/>']
    # legend (always present for >= 2 series): one row across the top, swatch + name in ink
    lx = L_
    for k, m in enumerate(M):
        o.append(f'<line x1="{lx}" y1="13" x2="{lx+14}" y2="13" stroke="{COL[k]}" stroke-width="3" stroke-dasharray="0.1 4.6" stroke-linecap="round"/>'
                 f'<text x="{lx+18}" y="17" font-size="11" fill="{INK}">{m}</text>')
        lx += 18 + 7 * len(m) + 16
    # recessive grid + axes
    for v in range(int(lo), int(hi) + 1, step):
        o.append(f'<line x1="{L_}" y1="{Y(v):.1f}" x2="{L_+pw}" y2="{Y(v):.1f}" stroke="{GRID}" stroke-width="1"/>'
                 f'<text x="{L_-6}" y="{Y(v)+3.5:.1f}" font-size="10" fill="{INK2}" text-anchor="end">{v}{unit}</text>')
    for i, w in enumerate(weeks):
        o.append(f'<text x="{X(i):.1f}" y="{T_+ph+15}" font-size="10" fill="{INK2}" text-anchor="middle">{w}</text>')
    o.append(f'<text x="{L_+pw/2:.1f}" y="{Ht-2}" font-size="10" fill="{INK2}" text-anchor="middle">{caption}</text>')
    # lines: dotted (round-capped dashes), small ringed markers, a native tooltip on each point
    for k, m in enumerate(M):
        p = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(pts[m]))
        o.append(f'<polyline points="{p}" fill="none" stroke="{COL[k]}" stroke-width="2.4" stroke-dasharray="0.1 4.6" stroke-linejoin="round" stroke-linecap="round"/>')
        for i, v in enumerate(pts[m]):
            o.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3" fill="{COL[k]}" stroke="{SURF}" stroke-width="1.5">'
                     f'<title>{m}, {tip} {weeks[i]}: {v:.1f}{unit}</title></circle>')
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
        # keep the stack inside the plot: push it up from the bottom edge (or down from the top), spacing preserved
        for j in range(len(ys) - 1, -1, -1):
            ys[j] = min(ys[j], T_ + ph + 2 - 12 * (len(ys) - 1 - j))
        for j in range(len(ys)):
            ys[j] = max(ys[j], T_ - 4 + 12 * j)
        for (y0, m, k), y in zip(lab, ys):
            x = X(len(weeks) - 1)
            o.append(f'<line x1="{x+4:.1f}" y1="{y0:.1f}" x2="{x+12:.1f}" y2="{y:.1f}" stroke="{COL[k]}" stroke-width="1"/>'
                     f'<text x="{x+15:.1f}" y="{y+3.5:.1f}" font-size="10" fill="{INK}">{m} {endv(pts[m][-1], unit)}{unit}</text>')
    o.append("</svg>")
    open(fname, "w").write("\n".join(o) + "\n")

    print(f"wrote {fname}")


line_chart("weekly_points.svg", [f"W{w}" for w in weeks], pts, 20, "",
           f"Points scored each week by each manager, Weeks 1 to {weeks[-1] if weeks else 0}",
           "Points by week: best-ball score in each finished week", "Week")

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
    # toilet bowl % over time: every earlier edition plus this one, x = the week each edition previewed
    ws = sorted(byweek)
    line_chart("toilet_trend.svg", [f"W{w}" for w in ws] + [f"W{START}"],
               {m: [last(byweek[w], m) for w in ws] + [last(cons, m)] for m in M}, 10, "%",
               f"Each manager's chance of finishing last, by weekly edition, Weeks {ws[0] if ws else START} to {START}",
               "Toilet bowl %: chance of finishing last, by the week each brief previewed", "edition for Week")
    print("wrote toilet.md\n" + "\n".join(t))
else:
    print("no agg.json yet: run src_agg.py first for toilet.md")
