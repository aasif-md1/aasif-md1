"""Builds all README SVGs (dark + light). Standard library only.
  GH_TOKEN=... python scripts/generate.py     real data (used by GitHub Actions)
  python scripts/generate.py --placeholder    card + 'waiting for data' panels
  python scripts/generate.py --sample DIR     fake data, preview only"""
import json, os, sys, random, pathlib, datetime as dt, urllib.request
from collections import deque
from html import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text())
W = 1000
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace"
THEMES = {
 "dark": dict(bg="#0d1117", panel="#161b22", line="#30363d", text="#ffffff", mute="#8b949e",
              levels=["#21262d", "#4a525c", "#767f89", "#aab2bb", "#e6edf3"],
              series=["#ffffff", "#c3cad2", "#98a1ab", "#707984", "#505862", "#373e47"], snake="#39d353"),
 "light": dict(bg="#ffffff", panel="#f6f8fa", line="#d0d7de", text="#1f2328", mute="#656d76",
              levels=["#ebedf0", "#c4cad0", "#98a0a8", "#656d76", "#24292f"],
              series=["#1f2328", "#424a53", "#656d76", "#8c959f", "#afb8c1", "#d0d7de"], snake="#1a7f37"),
}

def txt(x, y, s, fill, size=13, anchor="start", weight=400, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" {extra}>{escape(str(s))}</text>')

def rect(x, y, w, h, fill, r=3, extra=""):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" fill="{fill}" {extra}/>'

def svg(h, t, body, style=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
            f'font-family="{FONT}"><style>{style}</style>'
            f'{rect(.5, .5, W-1, h-1, t["panel"], 10, "stroke=%s" % chr(34) + t["line"] + chr(34))}{body}</svg>')

# ---------------------------------------------------------------- profile card
def card(name, t):
    art = (ROOT / "assets" / f"ascii-{name}.txt").read_text().rstrip("\n").split("\n")
    lh, cw, top = 7.0, 4.15, 50
    non_empty = [i for i, l in enumerate(art) if l.strip()]
    last_idx = non_empty[-1] if non_empty else 0
    min_lead = min((len(l) - len(l.lstrip()) for l in art if l.strip()), default=0)
    H = int(max(top + last_idx * lh + 2, 480))
    top_art = H - 2 - last_idx * lh
    b = [txt(22, 30, CFG["command"], t["mute"], 14)]
    for i, line in enumerate(art):
        if line.strip():
            lead = len(line) - len(line.lstrip()) - min_lead
            s = line.strip()
            b.append(txt(1.5 + lead*cw, top_art + i*lh, s, t["text"], 7, weight=700,
                         extra=f'xml:space="preserve" textLength="{len(s)*cw:.1f}" lengthAdjust="spacingAndGlyphs"'))
    x = 530
    rows = len(CFG["info"]) + len(CFG["contacts"])
    y = max(60, (H - (rows * 24 + 120)) / 2 + 20)
    for head, items in ((CFG["title"], CFG["info"]), ("contacts", CFG["contacts"])):
        b.append(txt(x, y, head, t["text"], 17, weight=700)); y += 14
        b.append(f'<line x1="{x}" y1="{y}" x2="{W-30}" y2="{y}" stroke="{t["line"]}"/>'); y += 24
        for k, v in items:
            if k: b.append(txt(x, y, k + ":", t["mute"], 13))
            b.append(txt(x + 96, y, v, t["text"], 13)); y += 24
        y += 28
    return svg(H, t, "".join(b))

# ---------------------------------------------------------------- data
QUERY = """query($login:String!){user(login:$login){id
 contributionsCollection{totalCommitContributions totalPullRequestContributions totalIssueContributions
  contributionYears contributionCalendar{totalContributions weeks{contributionDays{date contributionCount weekday}}}}
 repositories(first:100,ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC){totalCount
  nodes{name stargazerCount languages(first:20){edges{size node{name}}}}}}}"""

def gql(q, v):
    req = urllib.request.Request("https://api.github.com/graphql", json.dumps({"query": q, "variables": v}).encode(),
          {"Authorization": "bearer " + os.environ["GH_TOKEN"], "User-Agent": "profile-readme"})
    out = json.load(urllib.request.urlopen(req, timeout=60))
    if out.get("errors"): raise SystemExit(out["errors"])
    return out["data"]

def fetch():
    login = CFG["username"]
    u = gql(QUERY, {"login": login})["user"]
    c = u["contributionsCollection"]
    repos, langs, stars = [], {}, 0
    for r in u["repositories"]["nodes"]:
        stars += r["stargazerCount"]
        if r["name"].lower() == login.lower(): continue
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
        d = gql("""query($o:String!,$n:String!,$id:ID!){repository(owner:$o,name:$n){defaultBranchRef{target{
                 ... on Commit{history(author:{id:$id}){totalCount}}}}}}""",
                {"o": login, "n": r["name"], "id": u["id"]})["repository"]["defaultBranchRef"]
        repos.append((r["name"], d["target"]["history"]["totalCount"] if d else 0))
    years = {}
    for y in sorted(c["contributionYears"]):
        q = """query($l:String!,$f:DateTime!,$t:DateTime!){user(login:$l){contributionsCollection(from:$f,to:$t){
               contributionCalendar{totalContributions}}}}"""
        years[y] = gql(q, {"l": login, "f": f"{y}-01-01T00:00:00Z", "t": f"{y}-12-31T23:59:59Z"})[
            "user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    return dict(weeks=[[(d["date"], d["contributionCount"], d["weekday"]) for d in w["contributionDays"]]
                       for w in c["contributionCalendar"]["weeks"]],
                total=c["contributionCalendar"]["totalContributions"], commits=c["totalCommitContributions"],
                prs=c["totalPullRequestContributions"], issues=c["totalIssueContributions"],
                repo_count=u["repositories"]["totalCount"], stars=stars, repos=repos, langs=langs, years=years)

def sample():
    random.seed(7)
    today = dt.date(2026, 11, 26)
    d = today - dt.timedelta(days=364 + (today.weekday() + 1) % 7)
    weeks = []
    while d <= today:
        wd = (d.weekday() + 1) % 7
        if wd == 0 or not weeks: weeks.append([])
        n = random.randint(1, 11) if random.random() < .38 else 0
        weeks[-1].append((d.isoformat(), n, wd)); d += dt.timedelta(1)
    total = sum(x[1] for w in weeks for x in w)
    return dict(weeks=weeks, total=total, commits=int(total*.86), prs=14, issues=5, repo_count=10, stars=6,
        repos=[(f"sample-repo-{i}", v) for i, v in enumerate([142, 97, 76, 51, 38, 22, 9], 1)],
        langs={"JavaScript": 520, "TypeScript": 310, "Dart": 170, "CSS": 90, "HTML": 60, "Python": 25, "C++": 10},
        years={2024: 120, 2025: 480, 2026: total})

def streaks(days):
    best = run = 0
    for _, n, _ in days:
        run = run + 1 if n else 0; best = max(best, run)
    cur = 0
    seq = days[:-1] if days and not days[-1][1] else days  # today may still be empty
    for _, n, _ in reversed(seq):
        if not n: break
        cur += 1
    return cur, best

# ---------------------------------------------------------------- charts
def panel(t, x, y, w, h, title):
    return rect(x, y, w, h, t["bg"], 8, f'stroke="{t["line"]}"') + txt(x+18, y+28, title, t["text"], 14, weight=700)

def monthly_chart(name, t, x, y, w, h, labels, vals):
    """Render monthly contribution bars with gradient caps + smooth running-total area curve."""
    top = max(vals + [1])
    total = sum(vals)
    peak_i = vals.index(max(vals)) if vals else 0
    step = w / max(len(vals), 1)
    bw = min(step * 0.56, 46)
    defs = (
        f'<defs>'
        f'<linearGradient id="bar-{name}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{t["levels"][4]}" stop-opacity="0.95"/>'
        f'<stop offset="100%" stop-color="{t["levels"][1]}" stop-opacity="0.45"/>'
        f'</linearGradient>'
        f'<linearGradient id="peak-{name}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{t["snake"]}" stop-opacity="0.95"/>'
        f'<stop offset="100%" stop-color="{t["snake"]}" stop-opacity="0.22"/>'
        f'</linearGradient>'
        f'<linearGradient id="area-{name}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{t["snake"]}" stop-opacity="0.22"/>'
        f'<stop offset="100%" stop-color="{t["snake"]}" stop-opacity="0.01"/>'
        f'</linearGradient>'
        f'</defs>'
    )
    b = [defs]
    # Header legend & peak pill
    b.append(txt(x + w, y - 26, f'Peak: {labels[peak_i]} ({vals[peak_i]})  ·  Total: {total}', t["mute"], 11, "end"))
    # Subtle horizontal dashed gridlines
    for frac in (0.25, 0.5, 0.75, 1.0):
        gy = y + h - (h - 18) * frac
        b.append(f'<line x1="{x:.1f}" y1="{gy:.1f}" x2="{x+w:.1f}" y2="{gy:.1f}" '
                 f'stroke="{t["line"]}" stroke-dasharray="3 4" stroke-opacity="0.7"/>')
    b.append(f'<line x1="{x:.1f}" y1="{y+h:.1f}" x2="{x+w:.1f}" y2="{y+h:.1f}" stroke="{t["line"]}"/>')

    # Smooth cubic Bezier curve + area for running total (drawn behind bars & labels)
    acc, pts, s = 0, [], total or 1
    for i, v in enumerate(vals):
        acc += v
        pts.append((x + step * (i + 0.5), y + h - (h - 18) * acc / s))
    if len(pts) >= 2:
        d_path = [f"M {pts[0][0]:.1f},{pts[0][1]:.1f}"]
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            cx_mid = (x0 + x1) / 2
            d_path.append(f"C {cx_mid:.1f},{y0:.1f} {cx_mid:.1f},{y1:.1f} {x1:.1f},{y1:.1f}")
        curve = " ".join(d_path)
        area = f"{curve} L {pts[-1][0]:.1f},{y+h:.1f} L {pts[0][0]:.1f},{y+h:.1f} Z"
        b.append(f'<path d="{area}" fill="url(#area-{name})"/>')
        b.append(f'<path d="{curve}" fill="none" stroke="{t["snake"]}" stroke-width="2" stroke-opacity="0.85"/>')

    # Gradient bars + bright top cap + value labels
    for i, (l, v) in enumerate(zip(labels, vals)):
        cx = x + step * i + step / 2
        if v:
            bh = max((h - 18) * v / top, 6)
            by = y + h - bh
            grad = f"peak-{name}" if i == peak_i else f"bar-{name}"
            cap = t["snake"] if i == peak_i else t["text"]
            b.append(rect(cx - bw / 2, by, bw, bh, f"url(#{grad})", 4))
            b.append(rect(cx - bw / 2, by, bw, 2.5, cap, 1.5))
            b.append(txt(cx, by - 6, v, cap if i == peak_i else t["text"], 10, "middle",
                         700 if i == peak_i else 500,
                         extra=f'stroke="{t["bg"]}" stroke-width="3" paint-order="stroke"'))
        else:
            b.append(f'<circle cx="{cx:.1f}" cy="{y+h:.1f}" r="2.2" fill="{t["levels"][2]}"/>')
        b.append(txt(cx, y + h + 16, l, t["text"] if i == peak_i else t["mute"], 10, "middle",
                     700 if i == peak_i else 400))

    # Running total dots on top of bars so trajectory stays crisp
    for px, py in pts:
        b.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.2" fill="{t["snake"]}" stroke="{t["bg"]}" stroke-width="1.5"/>')
    return "".join(b)

def columns(t, x, y, w, h, labels, vals):
    top = max(vals + [1]); step = w / max(len(vals), 1); b = []
    for i, (l, v) in enumerate(zip(labels, vals)):
        bh = (h - 18) * v / top; bw = min(step * .64, 54); cx = x + step*i + step/2
        if v: b.append(rect(cx-bw/2, y+h-bh, bw, bh, t["levels"][3], 3))
        b.append(txt(cx, y+h-bh-5, v, t["text"], 10, "middle", extra=f'stroke="{t["bg"]}" stroke-width="3" paint-order="stroke"'))
        b.append(txt(cx, y+h+16, l, t["mute"], 10, "middle"))
    b.append(f'<line x1="{x}" y1="{y+h}" x2="{x+w}" y2="{y+h}" stroke="{t["line"]}"/>')
    return "".join(b)

def stats(name, t, d):
    days = [x for w in d["weeks"] for x in w]
    cur, best = streaks(days)
    b = [txt(22, 32, "$ git stats", t["mute"], 14)]
    tiles = [("Contributions (1y)", d["total"]), ("Commits (1y)", d["commits"]), ("Pull requests (1y)", d["prs"]),
             ("Public repos", d["repo_count"]), ("Current streak", f"{cur}d"), ("Longest streak (1y)", f"{best}d")]
    tw = (960 - 5*10) / 6
    for i, (k, v) in enumerate(tiles):
        x = 20 + i*(tw+10)
        b.append(rect(x, 48, tw, 76, t["bg"], 8, f'stroke="{t["line"]}"'))
        b.append(txt(x+tw/2, 86, v, t["text"], 26, "middle", 700))
        b.append(txt(x+tw/2, 108, k, t["mute"], 10, "middle"))
    # monthly columns + cumulative line
    months = {}
    for date, n, _ in days: months[date[:7]] = months.get(date[:7], 0) + n
    keys = sorted(months)[-12:]; vals = [months[k] for k in keys]
    b.append(panel(t, 20, 136, 960, 250, "Monthly contributions  (bars) + running total (curve)"))
    b.append(monthly_chart(name, t, 40, 190, 920, 165, [dt.date.fromisoformat(k+"-01").strftime("%b %y") for k in keys], vals))
    # language donut
    b.append(panel(t, 20, 398, 475, 260, "Languages used  (by code size)"))
    ls = sorted(d["langs"].items(), key=lambda a: -a[1])
    if len(ls) > 6: ls = ls[:5] + [("Other", sum(v for _, v in ls[5:]))]
    tot = sum(v for _, v in ls) or 1; off = 0
    for i, (n, v) in enumerate(ls):
        p = 100*v/tot
        b.append(f'<circle cx="135" cy="540" r="70" fill="none" stroke="{t["series"][i]}" stroke-width="30" '
                 f'pathLength="100" stroke-dasharray="{max(p-.5,.2):.2f} {100-max(p-.5,.2):.2f}" '
                 f'stroke-dashoffset="{-off:.2f}" transform="rotate(-90 135 540)"/>')
        off += p
        ly = 478 + i*27
        b.append(rect(255, ly-10, 11, 11, t["series"][i], 2))
        b.append(txt(275, ly, n, t["text"], 12)); b.append(txt(475, ly, f"{p:.1f}%", t["mute"], 12, "end"))
    b.append(txt(135, 545, len(d["langs"]), t["text"], 24, "middle", 700))
    b.append(txt(135, 562, "languages", t["mute"], 10, "middle"))
    # commits per repo
    b.append(panel(t, 505, 398, 475, 260, "Commits per repo  (all time, top 7)"))
    rs = sorted(d["repos"], key=lambda a: -a[1])[:7]; top = max([v for _, v in rs] + [1])
    for i, (n, v) in enumerate(rs):
        y = 446 + i*29; n = n if len(n) <= 20 else n[:19] + "…"
        b.append(txt(523, y+11, n, t["mute"], 11))
        b.append(rect(680, y, max(240*v/top, 2), 14, t["levels"][4 if i == 0 else 3], 3))
        b.append(txt(686 + max(240*v/top, 2), y+11, v, t["text"], 11))
    # weekday + yearly
    wk = [0]*7
    for _, n, w in days: wk[w] += n
    b.append(panel(t, 20, 670, 475, 210, "Active days of week  (1y)"))
    b.append(columns(t, 40, 724, 435, 125, "Sun Mon Tue Wed Thu Fri Sat".split(), wk))
    ys = sorted(d["years"].items())[-6:]
    b.append(panel(t, 505, 670, 475, 210, "Contributions by year"))
    b.append(columns(t, 525, 724, 435, 125, [str(k) for k, _ in ys], [v for _, v in ys]))
    return svg(900, t, "".join(b))

# ---------------------------------------------------------------- snake
COLS_Y = 7
def nbrs(c, cols):
    x, y = c
    for a, b in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
        if 0 <= a < cols and 0 <= b < COLS_Y: yield a, b

def search(body, food, cols):
    """Shortest path from head to the nearest food, never hitting the body.
    A body cell becomes free once the tail has moved past it."""
    n = len(body)
    free_at = {c: n - i for i, c in enumerate(body)}
    head = body[0]; prev = {head: None}; q = deque([(head, 0)])
    while q:
        c, k = q.popleft()
        for m in nbrs(c, cols):
            if m in prev or k + 1 < free_at.get(m, 0): continue
            prev[m] = c
            if m in food:
                path = [m]
                while prev[path[-1]] != head: path.append(prev[path[-1]])
                return path[::-1]
            q.append((m, k + 1))
    return None

def room(body, cols):
    seen = {body[0]}; q = [body[0]]; block = set(body[:-1])
    while q and len(seen) <= 30:
        for m in nbrs(q.pop(), cols):
            if m not in seen and m not in block: seen.add(m); q.append(m)
    return len(seen)

def simulate(food, cols, start, cap):
    """Returns head positions per step, {food: step eaten}, length per step."""
    body = [(x, 0) for x in range(start-1, -1, -1)]
    left = set(food); eaten = {}; heads = [body[0]]; lens = [len(body)]; size = len(body)
    for c in body:
        if c in left: left.remove(c); eaten[c] = 0
    limit = 8000
    while left and len(heads) < limit:
        path = search(body, left, cols)
        step = path[0] if path else None
        if step is None or room([step] + body[:size-1], cols) < size:
            safe = [m for m in nbrs(body[0], cols) if m not in body[:-1]]
            if not safe: break
            if step not in safe or room([step] + body[:size-1], cols) < size:
                step = max(safe, key=lambda m: room([m] + body[:size-1], cols))
        if step in left:
            left.remove(step); eaten[step] = len(heads); size = min(cap, size + 1)
        body = ([step] + body)[:size]
        heads.append(step); lens.append(len(body))
    # Return to (0, 0) and slide off the left edge before restarting
    home_steps = 0
    while body[0] != (0, 0) and home_steps < 300 and len(heads) < limit:
        path = search(body, {(0, 0)}, cols)
        step = path[0] if path else None
        if step is None:
            safe = [m for m in nbrs(body[0], cols) if m not in body[:-1]]
            if not safe:
                break
            step = min(safe, key=lambda m: m[0] + m[1])
        body = ([step] + body)[:size]
        heads.append(step); lens.append(len(body))
        home_steps += 1
    for k in range(1, size + 1):
        step = (-k, 0)
        body = ([step] + body)[:size]
        heads.append(step); lens.append(len(body))
    return heads, eaten, lens

def snake(name, t, d):
    s = CFG["snake"]; weeks = d["weeks"]; cols = len(weeks)
    cells = {(x, wd): n for x, w in enumerate(weeks) for _, n, wd in w}
    top = max(list(cells.values()) + [1])
    food = {c for c, n in cells.items() if n}
    heads, eaten, lens = simulate(food, cols, s["start_length"], s["max_length"])
    steps = len(heads) - 1; total = steps + 6; dur = total * s["seconds_per_step"]
    cell, gap = 14, 3.6; pitch = cell + gap
    ox = (W - (cols*pitch - gap)) / 2; oy = 62
    H = int(oy + 7*pitch + 20)
    pct = lambda k: f"{100*k/total:.3f}%"
    pos = lambda c: (ox + c[0]*pitch, oy + c[1]*pitch)
    css, b = [], [txt(22, 32, "$ ./snake --eat contributions", t["mute"], 14),
                  txt(W-22, 32, f'{d["total"]} contributions in the last year', t["text"], 12, "end")]
    for i, (c, n) in enumerate(sorted(cells.items())):
        x, y = pos(c)
        b.append(rect(x, y, cell, cell, t["levels"][0], 3))
        if n:
            lv = t["levels"][min(4, 1 + int(3*(n-1)/max(top-1, 1) + .5))]
            if c in eaten:
                k = eaten[c]
                css.append(f"@keyframes f{i}{{0%,{pct(max(k-.5,0))}{{opacity:1}}{pct(k)},99%{{opacity:0}}100%{{opacity:1}}}}"
                           f".f{i}{{animation:f{i} {dur:.2f}s linear infinite}}")
            b.append(rect(x, y, cell, cell, lv, 3, f'class="f{i}"'))
    for seg in range(s["max_length"] - 1, -1, -1):
        first = next((k for k, n in enumerate(lens) if n > seg), None)
        if first is None: continue
        # position of this segment at step k (the starting body lies along row 0)
        def at(k, seg=seg):
            j = k - seg
            return heads[j] if j >= 0 else (s["start_length"]-1 + j, 0)
        frames = []
        for k in range(steps + 1):
            c = at(k)
            vis = 1 if (k >= first and c[0] >= 0) else 0
            if 0 < k < steps:
                a, m, z = at(k-1), c, at(k+1)
                va = 1 if (k-1 >= first and a[0] >= 0) else 0
                vz = 1 if (k+1 >= first and z[0] >= 0) else 0
                if (m[0]-a[0], m[1]-a[1]) == (z[0]-m[0], z[1]-m[1]) and k != first and va == vis == vz:
                    continue
            x, y = pos(c)
            frames.append(f"{pct(k)}{{transform:translate({x:.1f}px,{y:.1f}px);opacity:{vis}}}")
        x, y = pos(at(steps)); frames.append(f"100%{{transform:translate({x:.1f}px,{y:.1f}px);opacity:0}}")
        css.append(f"@keyframes s{seg}{{{''.join(frames)}}}.s{seg}{{animation:s{seg} {dur:.2f}s linear infinite}}")
        sz = cell + 1 - seg*.55; off = (cell - sz) / 2
        x0, y0 = pos(at(0))
        b.append(f'<g class="s{seg}" transform="translate({x0:.1f} {y0:.1f})">'
                 + rect(off, off, sz, sz, t["snake"], 5 if seg == 0 else 4)
                 + ("".join(f'<circle cx="{cx}" cy="5" r="1.7" fill="{t["bg"]}"/>' for cx in (4.5, 9.5)) if seg == 0 else "")
                 + "</g>")
    return svg(H, t, "".join(b), "".join(css))

def buttons(name, t):
    c = t["mute"]
    specs = [
        ("btn-portfolio", "Portfolio", 104,
         '<circle cx="8" cy="8" r="6.2" fill="none" stroke="{c}" stroke-width="1.4"/>'
         '<ellipse cx="8" cy="8" rx="2.8" ry="6.2" fill="none" stroke="{c}" stroke-width="1.3"/>'
         '<line x1="1.8" y1="8" x2="14.2" y2="8" stroke="{c}" stroke-width="1.3"/>'),
        ("btn-linkedin", "LinkedIn", 96,
         '<rect x="1.5" y="1.5" width="13" height="13" rx="2.5" fill="none" stroke="{c}" stroke-width="1.4"/>'
         '<circle cx="5" cy="5.2" r="0.9" fill="{c}"/>'
         '<line x1="5" y1="7.5" x2="5" y2="12" stroke="{c}" stroke-width="1.5" stroke-linecap="round"/>'
         '<path d="M8 12V7.5M8 9.2c0-1.2 1-1.9 2-1.9s1.6.7 1.6 1.9V12" fill="none" stroke="{c}" stroke-width="1.5" stroke-linecap="round"/>'),
        ("btn-instagram", "Instagram", 106,
         '<rect x="1.5" y="1.5" width="13" height="13" rx="3.8" fill="none" stroke="{c}" stroke-width="1.4"/>'
         '<circle cx="8" cy="8" r="3" fill="none" stroke="{c}" stroke-width="1.4"/>'
         '<circle cx="11.8" cy="4.2" r="0.9" fill="{c}"/>'),
        ("btn-email", "Email", 78,
         '<rect x="1.5" y="3" width="13" height="10" rx="2" fill="none" stroke="{c}" stroke-width="1.4"/>'
         '<path d="M2 4l6 4.5L14 4" fill="none" stroke="{c}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'),
    ]
    out, h = {}, 26
    for key, label, w, icon in specs:
        body = (
            f'<g transform="translate(4,5)">{icon.format(c=c)}</g>'
            + txt(26, 17.5, label, t["text"], 13, "start", 500)
        )
        out[key] = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
                    f'font-family="{FONT}">{body}</svg>')
    return out

def waiting(t, label):
    return svg(150, t, txt(W/2, 70, label, t["text"], 16, "middle", 700) +
               txt(W/2, 100, "Waiting for data: Actions → Update profile README → Run workflow", t["mute"], 13, "middle"))

def main():
    args = sys.argv[1:]
    out = ROOT / "assets"
    if "--sample" in args:
        out = pathlib.Path(args[args.index("--sample")+1]); d = sample()
    elif "--placeholder" in args: d = None
    else: d = fetch()
    out.mkdir(parents=True, exist_ok=True)
    for name, t in THEMES.items():
        files = {"card": card(name, t),
                 "stats": stats(name, t, d) if d else waiting(t, "GitHub stats"),
                 "snake": snake(name, t, d) if d else waiting(t, "Contribution snake"),
                 **buttons(name, t)}
        if "--sample" in args:   # preview images must not pass as real stats
            for k in ("stats", "snake"):
                files[k] = files[k].replace("</svg>", txt(W/2, 32, "SAMPLE DATA (preview only)", "#d29922", 14, "middle", 700) + "</svg>")
        for k, v in files.items(): (out / f"{k}-{name}.svg").write_text(v)
    print("written to", out)

if __name__ == "__main__": main()
