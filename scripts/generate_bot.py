#!/usr/bin/env python3
"""
Commit Bot
----------
Turns your last 12 months of GitHub contributions into a little game board:
every active day is a tile (darker = more commits) and a small robot sweeps the
whole board column by column, gobbling up each tile as it rolls over it.
When the bot reaches the end, the board resets and it starts again (pure SVG animation).

    GITHUB_TOKEN=... python3 scripts/generate_bot.py --user aasif-md1 --out assets/bot.svg
    python3 scripts/generate_bot.py --mock  --out /tmp/bot.svg     # preview with fake data
    python3 scripts/generate_bot.py --empty --out assets/bot.svg   # placeholder
Standard library only; the GitHub Action runs it every night.
"""
import argparse, datetime as dt, json, os, random, sys, urllib.request

QUERY = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){
contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
MONO = "'JetBrains Mono','SF Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace"
SANS = "Inter,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
PAPER, PAPER2, INK, ACC, YEL, MUTE, TAN = "#f4efe4", "#fffaf0", "#15120f", "#ff5a36", "#ffd84a", "#6a6358", "#e6dccb"
LEVELS = ["#ece3d2", "#ffe99a", YEL, ACC, INK]
P = 14            # grid pitch
CELL = 11         # tile size
RUN = 26.0        # seconds the bot needs for one full sweep
PAUSE = 0.06      # fraction of the loop spent resting before reset


def fetch(login, token):
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    frm = now - dt.timedelta(days=364)
    body = json.dumps({"query": QUERY, "variables": {"login": login, "from": frm.isoformat().replace("+00:00", "Z"), "to": now.isoformat().replace("+00:00", "Z")}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "commit-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data or not data.get("data", {}).get("user"):
        raise SystemExit("GitHub API error: " + json.dumps(data)[:400])
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]], cal["totalContributions"]


def mock(seed=5):
    rnd, today, out, run = random.Random(seed), dt.date.today(), [], 0
    for i in range(364, -1, -1):
        if run: run -= 1; c = rnd.choice([1, 1, 2, 3, 5, 8, 12])
        elif rnd.random() < 0.10: run = rnd.randint(1, 6); c = rnd.choice([1, 2, 4])
        else: c = 0
        out.append(((today - dt.timedelta(days=i)).isoformat(), c))
    return out, sum(c for _, c in out)


def empty():
    t = dt.date.today()
    return [((t - dt.timedelta(days=i)).isoformat(), 0) for i in range(364, -1, -1)], 0


def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(days, total, login):
    W, H = 900, 262
    dates = [dt.date.fromisoformat(d) for d, _ in days]
    first_sun = dates[0] - dt.timedelta(days=(dates[0].weekday() + 1) % 7)
    ncols = (dates[-1] - first_sun).days // 7 + 1
    gx0 = (W - ncols * P) / 2 + (P - CELL) / 2
    gy0 = 84
    cell = {}
    for (ds, c), d in zip(days, dates):
        cell[((d - first_sun).days // 7, (d.weekday() + 1) % 7)] = (c, d)
    counts = sorted(c for c, _ in cell.values() if c > 0)

    def level(c):
        if c <= 0 or not counts: return 0
        q = sum(1 for x in counts if x <= c) / len(counts)
        return 1 if q <= .25 else 2 if q <= .5 else 3 if q <= .8 else 4

    order = []                                   # serpentine route over every cell
    for col in range(ncols):
        rows = range(7) if col % 2 == 0 else range(6, -1, -1)
        order += [(col, r) for r in rows]
    N = len(order)
    center = lambda col, row: (gx0 + col * P + CELL / 2, gy0 + row * P + CELL / 2)
    sx, sy = center(*order[0])
    path = "M0 0 " + " ".join(f"L{center(*c)[0] - sx:.1f} {center(*c)[1] - sy:.1f}" for c in order[1:])
    move = 1 - PAUSE
    dur = RUN / move
    tiles, active = [], 0
    for i, (col, row) in enumerate(order):
        if (col, row) not in cell: continue
        c, d = cell[(col, row)]
        lv = level(c)
        x, y = gx0 + col * P, gy0 + row * P
        if lv == 0:
            tiles.append(f'<rect x="{x:.1f}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{LEVELS[0]}"/>')
            continue
        active += 1
        t = i / (N - 1) * move
        tiles.append(
            f'<rect x="{x:.1f}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{LEVELS[lv]}" stroke="{INK}" stroke-width="1.3">'
            f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;{t:.4f};{t + .0006:.4f};{move + .02:.4f};1" dur="{dur:.1f}s" repeatCount="indefinite"/></rect>')
    months, seen = [], set()
    for (col, row), (c, d) in sorted(cell.items()):
        k = (d.year, d.month)
        if k not in seen and d.day <= 7 and row == 0:
            seen.add(k); months.append(f'<text x="{gx0 + col * P:.0f}" y="{gy0 + 7 * P + 20}" font-family="{MONO}" font-size="11" font-weight="700" fill="{MUTE}">{d.strftime("%b").upper()}</text>')
    lg = f'<text x="{W - 30 - 5 * 18 - 68}" y="{H - 24}" font-family="{MONO}" font-size="11" font-weight="700" fill="{MUTE}">LESS</text>'
    for i, f in enumerate(LEVELS):
        lg += f'<rect x="{W - 30 - 5 * 18 - 28 + i * 18}" y="{H - 34}" width="12" height="12" rx="2.5" fill="{f}" stroke="{INK if i else "none"}" stroke-width="1.3"/>'
    lg += f'<text x="{W - 30 - 28 + 4}" y="{H - 24}" font-family="{MONO}" font-size="11" font-weight="700" fill="{MUTE}">MORE</text>'
    bot = f'''<g transform="translate({sx:.1f} {sy:.1f})"><g>
<animateMotion dur="{dur:.1f}s" repeatCount="indefinite" calcMode="linear" keyPoints="0;1;1" keyTimes="0;{move:.4f};1" path="{path}"/>
<rect x="-9" y="-7" width="22" height="20" rx="5" fill="{INK}"/>
<rect x="-12" y="-10" width="22" height="20" rx="5" fill="{PAPER2}" stroke="{INK}" stroke-width="2.2"/>
<rect x="-7" y="-5" width="4.5" height="6" rx="1.5" fill="{INK}"><animate attributeName="height" values="6;6;1;6;6" keyTimes="0;.45;.5;.55;1" dur="3.4s" repeatCount="indefinite"/></rect>
<rect x="2" y="-5" width="4.5" height="6" rx="1.5" fill="{INK}"><animate attributeName="height" values="6;6;1;6;6" keyTimes="0;.45;.5;.55;1" dur="3.4s" repeatCount="indefinite"/></rect>
<rect x="-6" y="4" width="11" height="2.6" rx="1.3" fill="{ACC}"/>
<line x1="-1" y1="-10" x2="-1" y2="-16" stroke="{INK}" stroke-width="2"/>
<circle cx="-1" cy="-17" r="3.2" fill="{ACC}" stroke="{INK}" stroke-width="1.5"><animate attributeName="fill" values="{ACC};{YEL};{ACC}" dur="1.2s" repeatCount="indefinite"/></circle>
</g></g>'''
    note = f'<text x="{W / 2}" y="{gy0 + 3.5 * P}" text-anchor="middle" font-family="{MONO}" font-size="12.5" fill="{MUTE}">no tiles yet — the first nightly run will fill the board</text>' if total == 0 else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Commit Bot sweeping the contribution board of {esc(login)}: {total} contributions in the last 12 months"><title>Commit Bot — {total} contributions, last 12 months</title>
<rect width="{W}" height="{H}" fill="{PAPER}"/>
<rect x="9" y="9" width="{W - 14}" height="{H - 14}" rx="10" fill="{INK}"/><rect x="3" y="3" width="{W - 14}" height="{H - 14}" rx="10" fill="{PAPER2}" stroke="{INK}" stroke-width="3"/>
<text x="26" y="40" font-family="{MONO}" font-size="14" font-weight="800" letter-spacing="2" fill="{INK}">COMMIT BOT · CLEARING THE BOARD</text>
<text x="{W - 34}" y="40" text-anchor="end" font-family="{MONO}" font-size="12" font-weight="700" fill="{INK}"><tspan fill="{ACC}">{total}</tspan> contributions · {active} active days · last 12 months</text>
<line x1="3" y1="56" x2="{W - 11}" y2="56" stroke="{INK}" stroke-width="2.5"/>
{"".join(tiles)}{"".join(months)}{note}{lg}
{bot}
</svg>
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", default=os.environ.get("GH_USER", "aasif-md1")); ap.add_argument("--out", default="assets/bot.svg")
    ap.add_argument("--mock", action="store_true"); ap.add_argument("--empty", action="store_true")
    a = ap.parse_args()
    if a.mock: days, total = mock()
    elif a.empty: days, total = empty()
    else:
        tok = os.environ.get("GITHUB_TOKEN")
        if not tok: sys.exit("GITHUB_TOKEN not set (use --mock or --empty for previews)")
        days, total = fetch(a.user, tok)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(render(days, total, a.user))
    print(f"wrote {a.out}: {total} contributions")


if __name__ == "__main__":
    main()
