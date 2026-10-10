#!/usr/bin/env python3
"""
Builds assets/dashboard-dark.svg and assets/dashboard-light.svg for the profile README.

* In GitHub Actions (GITHUB_TOKEN set) it pulls live data from the GitHub API.
* Without a token / network it falls back to SNAPSHOT below, so it always produces a file.

Edit the CONFIG block to change text, links, technologies and the roadmap.
"""
import base64, html, json, math, os, sys, urllib.request
from datetime import date, datetime, timedelta

# ───────────────────────── CONFIG (edit me) ─────────────────────────
LOGIN = "aasif-md1"
NAME = "Aasif"
BIO = ["Student at Tribhuvan College,", "Neemrana — B.Sc. (Hons)", "Computer Science."]
LINKS = [  # (icon, text)
    ("pin", "Neemrana, Rajasthan"),
    ("cap", "Tribhuvan College, Neemrana"),
    ("link", "mdportfolio-eta.vercel.app"),
    ("link", "linkedin.com/in/md-aasif"),
    ("link", "instagram.com/__md_asif_01_"),
]
TECH = [  # (name, dot colour) — edit to match what you actually use
    ("JavaScript", "#f1e05a"), ("TypeScript", "#3178c6"), ("Dart", "#00b4ab"),
    ("Flutter", "#54c5f8"), ("React", "#61dafb"), ("Next.js", "#9aa4b2"),
    ("Node.js", "#6cc24a"), ("HTML", "#e34c26"), ("CSS", "#9b6bdf"),
    ("Git", "#f05133"), ("GitHub", "#8b949e"), ("Vercel", "#9aa4b2"),
]
ROADMAP = {"done": 4, "doing": 2, "todo": 3}  # shown as a progress bar
LANG_COLORS = {"JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Dart": "#00b4ab",
               "HTML": "#e34c26", "CSS": "#563d7c", "Python": "#3572A5", "Java": "#b07219",
               "C++": "#f34b7d", "C": "#555555", "Kotlin": "#A97BFF", "PHP": "#4F5D95"}

# Snapshot of public data (used when live fetch is unavailable). Refreshed automatically by the Action.
SNAPSHOT = {
    "created_at": "2024-01-09T13:33:51Z",
    "followers": 1, "public_repos": 11,
    "repos": [  # name, language, stars, forks
        ("watch-party-app", "JavaScript", 1, 0), ("ai-resume-builder", "JavaScript", 1, 0),
        ("tribhuvan_portal", "TypeScript", 1, 0), ("md.portfolio", "TypeScript", 1, 0),
        ("MultimodelAI", "JavaScript", 1, 0), ("NoteSpace", "Dart", 1, 0),
    ],
    "days": {"2025-12-27": 3, "2026-02-19": 11, "2026-02-24": 1, "2026-02-25": 1, "2026-03-06": 2,
             "2026-03-07": 11, "2026-03-08": 2, "2026-03-09": 10, "2026-03-10": 1, "2026-04-01": 8,
             "2026-04-02": 4, "2026-04-10": 2, "2026-04-14": 2, "2026-04-30": 1, "2026-07-04": 4,
             "2026-08-06": 4, "2026-08-07": 35, "2026-08-08": 3, "2026-08-09": 2, "2026-08-10": 12,
             "2026-08-17": 1, "2026-08-23": 9, "2026-08-27": 17, "2026-08-28": 18, "2026-08-29": 17,
             "2026-09-03": 1, "2026-09-06": 1, "2026-09-07": 1, "2026-09-12": 1, "2026-09-14": 2,
             "2026-09-28": 2, "2026-10-02": 2, "2026-10-09": 3},
}

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"

THEMES = {
    "dark": dict(bg="#0d1117", text="#c9d1d9", strong="#f0f6fc", muted="#8b949e", link="#58a6ff",
                 line="#30363d", chip="#161b22", lv=["#21262d", "#0e4429", "#006d32", "#26a641", "#39d353"],
                 shade=(0.22, 0.42), doing="#8957e5", todo="#30363d", ok="#3fb950"),
    "light": dict(bg="#ffffff", text="#24292f", strong="#1f2328", muted="#656d76", link="#0969da",
                  line="#d0d7de", chip="#f6f8fa", lv=["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
                  shade=(0.10, 0.22), doing="#8250df", todo="#d0d7de", ok="#1a7f37"),
}

# ───────────────────────── DATA ─────────────────────────
def gh(path, token, data=None):
    req = urllib.request.Request("https://api.github.com" + path, data=data)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("User-Agent", "profile-dashboard")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def load_data(today):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    d = {"created_at": SNAPSHOT["created_at"], "followers": SNAPSHOT["followers"],
         "public_repos": SNAPSHOT["public_repos"], "repos": list(SNAPSHOT["repos"]),
         "days": dict(SNAPSHOT["days"]), "avatar": None, "live": False}
    if not token:
        return d
    try:
        u = gh(f"/users/{LOGIN}", token)
        repos = gh(f"/users/{LOGIN}/repos?per_page=100&sort=pushed", token)
        repos = [r for r in repos if not r["fork"] and r["name"].lower() != LOGIN.lower()]
        q = json.dumps({"query": "query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}",
                        "variables": {"l": LOGIN}}).encode()
        cal = gh("/graphql", token, q)["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        days = {x["date"]: x["contributionCount"] for w in cal for x in w["contributionDays"] if x["contributionCount"]}
        d.update(created_at=u["created_at"], followers=u["followers"], public_repos=u["public_repos"],
                 repos=[(r["name"], r["language"], r["stargazers_count"], r["forks_count"]) for r in repos],
                 days=days, live=True)
    except Exception as e:  # keep the snapshot if anything fails
        print("live fetch failed, using snapshot:", e, file=sys.stderr)
    try:
        req = urllib.request.Request(f"https://github.com/{LOGIN}.png?size=300", headers={"User-Agent": "profile-dashboard"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d["avatar"] = "data:image/png;base64," + base64.b64encode(r.read()).decode()
    except Exception as e:
        print("avatar unavailable, using monogram:", e, file=sys.stderr)
    return d


# ───────────────────────── HELPERS ─────────────────────────
def esc(s): return html.escape(str(s), quote=True)


def mix(hexc, amt):  # darken towards black
    h = hexc.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * (1 - amt)), int(g * (1 - amt)), int(b * (1 - amt)))


def ago(delta_days):
    if delta_days < 1: return "today"
    if delta_days < 2: return "1 day ago"
    if delta_days < 31: return f"{int(delta_days)} days ago"
    if delta_days < 365: return f"{int(delta_days // 30)} months ago"
    y = int(delta_days // 365)
    return f"{y} year{'s' if y > 1 else ''} ago"


ICONS = {
    "cal": '<rect x="2" y="3" width="12" height="11" rx="2"/><path d="M2 7h12M5 1.5v3M11 1.5v3"/>',
    "people": '<circle cx="6" cy="5" r="2.4"/><path d="M1.5 13.5c0-2.6 2-4 4.5-4s4.5 1.4 4.5 4"/><path d="M10.5 3a2.2 2.2 0 0 1 0 4.2M12 9.8c1.6.4 2.5 1.6 2.5 3.4"/>',
    "repo": '<path d="M3 13V3a1.5 1.5 0 0 1 1.5-1.5H13v10H4.5A1.5 1.5 0 0 0 3 13zm0 0a1.5 1.5 0 0 0 1.5 1.5H13"/>',
    "star": '<path d="M8 1.6l2 4.2 4.6.6-3.4 3.2.9 4.6L8 11.8 3.9 14.2l.9-4.6L1.4 6.4l4.6-.6z"/>',
    "fork": '<circle cx="4" cy="3.5" r="1.7"/><circle cx="12" cy="3.5" r="1.7"/><circle cx="8" cy="12.5" r="1.7"/><path d="M4 5.2v1.3c0 1 .8 1.8 1.8 1.8h4.4c1 0 1.8-.8 1.8-1.8V5.2M8 8.3v2.5"/>',
    "link": '<path d="M6.5 9.5l3-3M7 4.2l.9-.9a2.7 2.7 0 0 1 3.8 3.8l-.9.9M9 11.8l-.9.9a2.7 2.7 0 0 1-3.8-3.8l.9-.9"/>',
    "pin": '<path d="M8 14.5s4.5-4 4.5-7.5a4.5 4.5 0 0 0-9 0c0 3.5 4.5 7.5 4.5 7.5z"/><circle cx="8" cy="7" r="1.6"/>',
    "cap": '<path d="M8 2.5L1 6l7 3.5L15 6 8 2.5zM3.5 7.6V11c0 1 2 2.2 4.5 2.2s4.5-1.2 4.5-2.2V7.6"/>',
    "flame": '<path d="M8 1.5c.5 2.5 3.5 4 3.5 7.5a3.5 3.5 0 0 1-7 0c0-1.5.7-2.5 1.5-3.3.1 1 .6 1.6 1.2 1.9C7 5.8 7.2 3.5 8 1.5z"/>',
    "graph": '<path d="M2 2v12h12M5 10l2.5-3 2 2L13 4.5"/>',
    "code": '<path d="M5.5 4.5L2 8l3.5 3.5M10.5 4.5L14 8l-3.5 3.5"/>',
    "clock": '<circle cx="8" cy="8" r="6"/><path d="M8 4.5V8l2.3 1.5"/>',
    "check": '<path d="M3 8.5l3.2 3.2L13 4.8"/>',
}


def icon(name, x, y, color, size=15):
    k = size / 16
    return f'<g transform="translate({x},{y}) scale({k:.3f})" fill="none" stroke="{color}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>'


def text(x, y, s, size=13, fill="#fff", weight=400, anchor="start", extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{esc(s)}</text>'


def heading(x, y, ic, label, T):
    return icon(ic, x, y - 12, T["muted"]) + text(x + 22, y, label, 15, T["link"], 500)


# ───────────────────────── CALENDAR ─────────────────────────
def build_calendar(days, today):
    start = today - timedelta(days=364)
    start -= timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    cols = ((today - start).days // 7) + 1
    cells = []  # (col,row,date,count)
    for c in range(cols):
        for r in range(7):
            dt = start + timedelta(days=c * 7 + r)
            if dt > today: continue
            cells.append((c, r, dt, int(days.get(dt.isoformat(), 0))))
    return cols, cells


def stats(cells, today):
    series = [(dt, n) for _, _, dt, n in cells]
    total = sum(n for _, n in series)
    active = sum(1 for _, n in series if n)
    best = max(series, key=lambda x: x[1])
    longest = cur = 0
    for _, n in series:
        cur = cur + 1 if n else 0
        longest = max(longest, cur)
    cs = 0
    i = len(series) - 1
    if series[i][1] == 0: i -= 1  # today not over yet
    while i >= 0 and series[i][1]: cs += 1; i -= 1
    last = max((dt for dt, n in series if n), default=None)
    wd = [0] * 7
    for dt, n in series: wd[(dt.weekday() + 1) % 7] += n
    months = []
    y, m = today.year, today.month
    for k in range(11, -1, -1):
        mm = m - k; yy = y
        while mm <= 0: mm += 12; yy -= 1
        months.append(((yy, mm), sum(n for dt, n in series if (dt.year, dt.month) == (yy, mm))))
    return dict(total=total, active=active, best=best, longest=longest, current=cs, last=last, wd=wd, months=months)


def iso_calendar(cells, cols, ox, oy, s, T):
    mx = max((n for *_, n in cells), default=1) or 1
    c30 = math.cos(math.radians(30))
    f = 0.9
    def P(i, j, z): return (ox + (i - j) * c30 * s, oy + (i + j) * 0.5 * s - z)
    def pts(*ps): return " ".join(f"{x:.1f},{y:.1f}" for x, y in ps)
    out = []
    for c, r, dt, n in sorted(cells, key=lambda t: (t[0] + t[1], t[0])):
        lvl = 0 if n == 0 else min(4, max(1, math.ceil(n / mx * 4)))
        base = T["lv"][lvl]
        h = 0.8 if n == 0 else 3 + 34 * math.sqrt(n / mx)
        top = pts(P(c, r, h), P(c + f, r, h), P(c + f, r + f, h), P(c, r + f, h))
        left = pts(P(c, r + f, 0), P(c + f, r + f, 0), P(c + f, r + f, h), P(c, r + f, h))
        right = pts(P(c + f, r, 0), P(c + f, r + f, 0), P(c + f, r + f, h), P(c + f, r, h))
        out.append(f'<polygon points="{left}" fill="{mix(base, T["shade"][0])}"/><polygon points="{right}" fill="{mix(base, T["shade"][1])}"/><polygon points="{top}" fill="{base}"/>')
    return "".join(out)


# ───────────────────────── RENDER ─────────────────────────
def render(theme, D, today):
    T = THEMES[theme]
    W, H = 1000, 640
    cols, cells = build_calendar(D["days"], today)
    S = stats(cells, today)
    created = datetime.strptime(D["created_at"][:10], "%Y-%m-%d").date()
    repos = D["repos"]
    stars = sum(r[2] for r in repos); forks = sum(r[3] for r in repos)
    o = []

    # left column ─ identity
    cx, cy, r = 140, 118, 84
    o.append(f'<defs><clipPath id="av"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath></defs>')
    if D["avatar"]:
        o.append(f'<image href="{D["avatar"]}" x="{cx-r}" y="{cy-r}" width="{2*r}" height="{2*r}" clip-path="url(#av)" preserveAspectRatio="xMidYMid slice"/>')
    else:
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{T["chip"]}"/>' + text(cx, cy + 28, NAME[0].upper(), 84, T["muted"], 300, "middle"))
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{T["line"]}" stroke-width="2"/>')
    o.append(text(54, 262, NAME, 26, T["strong"], 600))
    o.append(text(54, 288, LOGIN, 18, T["muted"], 300))
    for i, line in enumerate(BIO):
        o.append(text(54, 322 + i * 19, line, 13.5, T["text"]))
    y = 398
    for ic, t in LINKS:
        o.append(icon(ic, 54, y - 12, T["muted"]) + text(76, y, t, 13, T["text"]))
        y += 27
    o.append(f'<circle cx="60" cy="{y+14}" r="4.5" fill="{T["ok"]}"/>' + text(76, y + 19, "Open to internships & collabs", 13, T["muted"]))

    # middle column
    X = 320
    o.append(text(X, 44, NAME, 21, T["link"], 600))
    rows = [("cal", f"Joined GitHub {ago((today - created).days)}"),
            ("people", f"Followed by {D['followers']} user{'s' if D['followers'] != 1 else ''}"),
            ("clock", f"Last active {ago((today - S['last']).days)}" if S["last"] else "No recent activity")]
    for i, (ic, t) in enumerate(rows):
        o.append(icon(ic, X, 62 + i * 24 - 12, T["muted"]) + text(X + 22, 62 + i * 24, t, 13.5, T["muted"]))
    o.append(heading(X, 158, "repo", f"{D['public_repos']} Repositories", T))
    for i, (ic, t) in enumerate([("star", f"{stars} Stargazers"), ("fork", f"{forks} Forks"),
                                  ("code", f"{len({r[1] for r in repos if r[1]})} Languages")]):
        o.append(icon(ic, X + 190 * (i % 2), 176 + (i // 2) * 24, T["muted"]) + text(X + 22 + 190 * (i % 2), 188 + (i // 2) * 24, t, 13.5, T["muted"]))

    # contributions per month
    o.append(heading(X, 252, "graph", "Contribution activity per month", T))
    mx = max([v for _, v in S["months"]] + [1]); bx, bw, pitch, base = X, 20, 28.3, 336
    for k, ((yy, mm), v) in enumerate(S["months"]):
        h = max(1.5, 62 * v / mx); x = bx + k * pitch
        o.append(f'<rect x="{x:.1f}" y="{base-h:.1f}" width="{bw}" height="{h:.1f}" rx="2" fill="{T["lv"][3] if v else T["lv"][0]}"/>')
        if v: o.append(text(x + bw / 2, base - h - 4, v, 10.5, T["text"], 400, "middle"))
        o.append(text(x + bw / 2, base + 15, "JFMAMJJASOND"[mm - 1], 10.5, T["muted"], 400, "middle"))

    # weekday bars + streaks
    o.append(heading(X, 392, "cal", "Activity per weekday", T))
    mw = max(S["wd"] + [1]); base2 = 480
    for k, v in enumerate(S["wd"]):
        h = max(1.5, 52 * v / mw); x = X + k * 21
        o.append(f'<rect x="{x:.1f}" y="{base2-h:.1f}" width="13" height="{h:.1f}" rx="2" fill="{T["lv"][3] if v else T["lv"][0]}"/>')
        if v: o.append(text(x + 6.5, base2 - h - 4, v, 10, T["text"], 400, "middle"))
        o.append(text(x + 6.5, base2 + 14, "SMTWTFS"[k], 10.5, T["muted"], 400, "middle"))
    sx = X + 158
    bd, bn = S["best"]
    items = [("flame", "Streak", f"{S['current']} day{'s' if S['current'] != 1 else ''}"),
             ("flame", "Longest", f"{S['longest']} days"),
             ("check", "Active days", f"{S['active']}"),
             ("star", "Best day", f"{bn} · {bd.strftime('%b')} {bd.day}")]
    for i, (ic, a, b) in enumerate(items):
        yy = 420 + i * 25
        o.append(icon(ic, sx, yy - 12, T["muted"]) + text(sx + 22, yy, a, 13, T["muted"]) + text(sx + 182, yy, b, 13, T["strong"], 600, "end"))

    # technologies as chips
    o.append(heading(X, 534, "code", "Technologies", T))
    x, y = X, 548
    for name, col in TECH:
        w = 30 + len(name) * 6.9
        if x + w > X + 340: x = X; y += 26
        o.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="21" rx="10.5" fill="{T["chip"]}" stroke="{T["line"]}"/><circle cx="{x+11:.1f}" cy="{y+10.5}" r="4" fill="{col}"/>' + text(x + 21, y + 14.5, name, 11.5, T["text"]))
        x += w + 6

    # right column
    RX = 690
    o.append(heading(RX, 44, "cal", "Contributions calendar", T))
    o.append(iso_calendar(cells, cols, RX + 6 * 0.866 * 5.5 + 1, 92, 5.5, T))
    o.append(icon("flame", RX, 268 - 12, T["muted"]) + text(RX + 22, 268, f"{S['total']} contributions in the last year", 12.5, T["muted"]))

    o.append(heading(RX, 322, "repo", "Repositories", T))
    for i, (n, lang, st, fk) in enumerate(repos[:6]):
        yy = 350 + i * 25
        o.append(text(RX, yy, n, 13, T["link"]))
        o.append(f'<circle cx="{RX+168}" cy="{yy-4}" r="4" fill="{LANG_COLORS.get(lang, T["muted"])}"/>' + text(RX + 177, yy, lang or "—", 11.5, T["muted"]))
        o.append(icon("star", RX + 256, yy - 11, T["muted"], 12) + text(RX + 272, yy, st, 11.5, T["muted"]))

    langs = {}
    for _, lang, *_ in repos:
        if lang: langs[lang] = langs.get(lang, 0) + 1
    tot = sum(langs.values()) or 1
    o.append(heading(RX, 528, "code", "Most used languages", T))
    x = RX; bar = []
    items_l = sorted(langs.items(), key=lambda kv: -kv[1])
    for k, (lg, c) in enumerate(items_l):
        w = 280 * c / tot
        bar.append(f'<rect x="{x:.1f}" y="540" width="{w:.1f}" height="8" fill="{LANG_COLORS.get(lg, T["muted"])}"/>'); x += w
    o.append(f'<clipPath id="lb"><rect x="{RX}" y="540" width="280" height="8" rx="4"/></clipPath><g clip-path="url(#lb)">{"".join(bar)}</g>')
    lx = RX
    for lg, c in items_l:
        o.append(f'<circle cx="{lx+4}" cy="566" r="4" fill="{LANG_COLORS.get(lg, T["muted"])}"/>' + text(lx + 12, 570, f"{lg} {round(100*c/tot)}%", 11, T["muted"]))
        lx += 12 + (len(lg) + 4) * 6.1 + 14

    rd = ROADMAP; rt = sum(rd.values()) or 1
    o.append(heading(RX, 604, "check", "Roadmap", T))
    segs = [("done", T["ok"]), ("doing", T["doing"]), ("todo", T["todo"])]
    o.append(f'<clipPath id="rb"><rect x="{RX+96}" y="595" width="184" height="8" rx="4"/></clipPath><g clip-path="url(#rb)">')
    x = RX + 96
    for k, col in segs:
        w = 184 * rd[k] / rt; o.append(f'<rect x="{x:.1f}" y="595" width="{w:.1f}" height="8" fill="{col}"/>'); x += w
    o.append("</g>")
    o.append(text(RX + 280, 624, f"{rd['done']} done · {rd['doing']} doing · {rd['todo']} todo", 11, T["muted"], 400, "end"))

    body = "".join(o)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}" role="img" aria-label="GitHub profile dashboard for {esc(LOGIN)}: {S['total']} contributions in the last year, {len(repos)} featured repositories, languages and roadmap.">
<rect width="{W}" height="{H}" rx="10" fill="{T["bg"]}"/><rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="10" fill="none" stroke="{T["line"]}"/>
{body}
</svg>'''


def main():
    today = date.today()
    D = load_data(today)
    os.makedirs(OUT, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(OUT, f"dashboard-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(render(theme, D, today))
    print("written; live data:", D["live"])


if __name__ == "__main__":
    main()
