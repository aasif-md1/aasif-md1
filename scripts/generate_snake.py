#!/usr/bin/env python3
"""
Commit Snake
------------
Your last 12 months of GitHub contributions become a board of tiles (darker = more commits).
A little snake hunts down every active tile, always taking the shortest route to the nearest
uneaten one (and eating anything it crosses on the way). Each tile it eats adds a body segment in
the SAME colour right behind its head, and the oldest segment drops off the tail so the body never
exceeds MAX_BODY dots. When the board is clear it takes the shortest way home, then the board
resets and the hunt starts again (pure SVG animation).

    GITHUB_TOKEN=... python3 scripts/generate_snake.py --user aasif-md1 --out assets/snake.svg
    python3 scripts/generate_snake.py --mock  --out /tmp/snake.svg    # preview with fake data
    python3 scripts/generate_snake.py --empty --out assets/snake.svg  # placeholder
Standard library only; the GitHub Action runs it every night.
"""
import argparse, datetime as dt, heapq, json, os, random, sys, urllib.request

QUERY = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){
contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
MONO = "'JetBrains Mono','SF Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace"
PAPER, PAPER2, INK, ACC, YEL, MUTE = "#f4efe4", "#fffaf0", "#15120f", "#ff5a36", "#ffd84a", "#6a6358"
LEVELS = ["#ece3d2", "#ffe99a", YEL, ACC, INK]
P, CELL = 14, 11          # grid pitch / tile size
STEP = 0.15               # seconds per cell (bigger = slower snake)
END_PAUSE = 2.5           # seconds to rest before the board resets
MAX_BODY = 10             # body never has more than this many coloured dots; the oldest drops off the tail


def fetch(login, token):
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    frm = now - dt.timedelta(days=364)
    body = json.dumps({"query": QUERY, "variables": {"login": login, "from": frm.isoformat().replace("+00:00", "Z"), "to": now.isoformat().replace("+00:00", "Z")}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "commit-snake"})
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
    gx0, gy0 = (W - ncols * P) / 2 + (P - CELL) / 2, 84
    cell = {((d - first_sun).days // 7, (d.weekday() + 1) % 7): (c, d) for (ds, c), d in zip(days, dates)}
    counts = sorted(c for c, _ in cell.values() if c > 0)

    def level(c):
        if c <= 0 or not counts: return 0
        q = sum(1 for x in counts if x <= c) / len(counts)
        return 1 if q <= .25 else 2 if q <= .5 else 3 if q <= .8 else 4

    active = {pos for pos, (c, _) in cell.items() if level(c) > 0}
    start = (0, 0)

    DIRS = ((1, 0), (0, 1), (0, -1), (-1, 0))          # right, down, up, left: no diagonal moves ever

    def find_path(src, goals, blocked, heading):
        """Shortest grid path to the nearest goal; among equally short paths, the one with the fewest
        turns (so it runs in straight lines instead of zig-zagging like a staircase)."""
        s0 = (src, heading)
        dist, prev, heap, cnt = {s0: (0, 0)}, {s0: None}, [(0, 0, 0, s0)], 1
        while heap:
            steps, turns, _, state = heapq.heappop(heap)
            if dist.get(state) != (steps, turns): continue
            cur, hd = state
            if cur in goals and cur != src:
                out = []
                while state is not None:
                    out.append(state[0]); state = prev[state]
                return out[::-1][1:]
            for d in DIRS:
                nb = (cur[0] + d[0], cur[1] + d[1])
                if not (0 <= nb[0] < ncols and 0 <= nb[1] < 7) or nb in blocked: continue
                nd = (steps + 1, turns + (hd is not None and d != hd))
                ns = (nb, d)
                if ns not in dist or nd < dist[ns]:
                    dist[ns], prev[ns] = nd, state
                    heapq.heappush(heap, (nd[0], nd[1], cnt, ns)); cnt += 1
        return None

    def bfs(src, goals, blocked):
        h = (route[-1][0] - route[-2][0], route[-1][1] - route[-2][1]) if len(route) > 1 else None
        return find_path(src, goals, blocked, h)

    route, eat_idx = [start], {}
    if start in active: eat_idx[start] = 0
    todo = active - set(eat_idx)
    while todo:
        body_cells = set(route[-MAX_BODY - 1:-1])      # try not to cross its own body
        path = bfs(route[-1], todo, body_cells) or bfs(route[-1], todo, set())
        for c in path:
            route.append(c)
            if c in todo: todo.discard(c); eat_idx[c] = len(route) - 1
    if route[-1] != start:                             # shortest way home
        route += bfs(route[-1], {start}, set(route[-MAX_BODY - 1:-1])) or bfs(route[-1], {start}, set())
    if len(route) < 2: route = [start, start]
    M = len(route) - 1
    D = M * STEP + END_PAUSE                           # one full loop, seconds
    m = M * STEP / D                                   # fraction of the loop spent moving
    center = lambda c: (gx0 + c[0] * P + CELL / 2, gy0 + c[1] * P + CELL / 2)
    sx, sy = center(route[0])
    path = "M0 0 " + " ".join(f"L{center(c)[0] - sx:.1f} {center(c)[1] - sy:.1f}" for c in route[1:])
    motion = f'dur="{D:.2f}s" repeatCount="indefinite" calcMode="linear" keyPoints="0;1;1" keyTimes="0;{m:.5f};1" path="{path}"'
    kt = lambda t: f"{min(t / D, .9995):.5f}"
    print(f"route: {M} steps, loop {D:.1f}s, {len(active)} tiles", file=sys.stderr)

    tiles, eaten = [], []                              # eaten = (time, colour) in eating order
    for pos in sorted(cell):
        c, d = cell[pos]
        lv = level(c)
        x, y = gx0 + pos[0] * P, gy0 + pos[1] * P
        if lv == 0:
            tiles.append(f'<rect x="{x:.1f}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{LEVELS[0]}"/>')
            continue
        t = eat_idx[pos] * STEP
        eaten.append((t, LEVELS[lv]))
        tiles.append(f'<rect x="{x:.1f}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{LEVELS[lv]}" stroke="{INK}" stroke-width="1.3">'
                     f'<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;{kt(t)};{kt(t + .05)};.9995;1" dur="{D:.2f}s" repeatCount="indefinite"/></rect>')
    eaten.sort()
    n = len(eaten)

    body = []                                          # far end first so the neck is drawn on top
    for k in range(min(n, MAX_BODY), 0, -1):
        tk = eaten[k - 1][0]
        times, cols = [0.0], [eaten[0][1]]
        for j in range(k, n + 1):                      # after the j-th meal, segment k shows meal j-k+1
            times.append(eaten[j - 1][0]); cols.append(eaten[j - k][1])
        keyt = ";".join(kt(t) if i else "0" for i, t in enumerate(times)) + ";1"
        vals = ";".join(cols) + ";" + cols[-1]
        sz = 12 - max(0, k - 6) * .75                   # the last few segments taper like a tail
        body.append(
            f'<g transform="translate({sx:.1f} {sy:.1f})"><rect x="{-sz / 2:g}" y="{-sz / 2:g}" width="{sz}" height="{sz}" rx="{sz * .3:.1f}" fill="{cols[0]}" stroke="{INK}" stroke-width="1.6" opacity="0">'
            f'<animateMotion begin="{k * STEP:.2f}s" {motion}/>'
            f'<animate attributeName="fill" values="{vals}" keyTimes="{keyt}" calcMode="discrete" dur="{D:.2f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;1;0;0" keyTimes="0;{kt(tk)};.9995;1" calcMode="discrete" dur="{D:.2f}s" repeatCount="indefinite"/></rect></g>')

    head = f'''<g transform="translate({sx:.1f} {sy:.1f})"><g>
<animateMotion rotate="auto" {motion}/>
<rect x="-7" y="-7" width="14" height="14" rx="4.6" fill="{PAPER2}" stroke="{INK}" stroke-width="2.2"/>
<circle cx="2.4" cy="-2.7" r="1.5" fill="{INK}"/><circle cx="2.4" cy="2.7" r="1.5" fill="{INK}"/>
</g></g>'''

    months, seen = [], set()
    for (col, row), (c, d) in sorted(cell.items()):
        k = (d.year, d.month)
        if k not in seen and d.day <= 7 and row == 0:
            seen.add(k); months.append(f'<text x="{gx0 + col * P:.0f}" y="{gy0 + 7 * P + 20}" font-family="{MONO}" font-size="11" font-weight="700" fill="{MUTE}">{d.strftime("%b").upper()}</text>')
    lx = W - 30 - 5 * 18 - 68
    lg = f'<text x="{lx}" y="{H - 24}" font-family="{MONO}" font-size="11" font-weight="700" fill="{MUTE}">LESS</text>'
    for i, f in enumerate(LEVELS):
        lg += f'<rect x="{lx + 40 + i * 18}" y="{H - 34}" width="12" height="12" rx="2.5" fill="{f}" stroke="{INK if i else "none"}" stroke-width="1.3"/>'
    lg += f'<text x="{lx + 40 + 5 * 18 + 4}" y="{H - 24}" font-family="{MONO}" font-size="11" font-weight="700" fill="{MUTE}">MORE</text>'
    note = f'<text x="{W / 2}" y="{gy0 + 3.5 * P}" text-anchor="middle" font-family="{MONO}" font-size="12.5" fill="{MUTE}">no tiles yet — the first nightly run will fill the board</text>' if total == 0 else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="A snake eating the contribution board of {esc(login)}: {total} contributions in the last 12 months"><title>Commit Snake — {total} contributions, last 12 months</title>
<rect width="{W}" height="{H}" fill="{PAPER}"/>
<rect x="9" y="9" width="{W - 14}" height="{H - 14}" rx="10" fill="{INK}"/><rect x="3" y="3" width="{W - 14}" height="{H - 14}" rx="10" fill="{PAPER2}" stroke="{INK}" stroke-width="3"/>
<text x="26" y="40" font-family="{MONO}" font-size="14" font-weight="800" letter-spacing="2" fill="{INK}">COMMIT SNAKE · EATING THE YEAR</text>
<text x="{W - 34}" y="40" text-anchor="end" font-family="{MONO}" font-size="12" font-weight="700" fill="{INK}"><tspan fill="{ACC}">{total}</tspan> contributions · {n} active days · last 12 months</text>
<line x1="3" y1="56" x2="{W - 11}" y2="56" stroke="{INK}" stroke-width="2.5"/>
{"".join(tiles)}{"".join(months)}{note}{lg}
{"".join(body)}
{head}
</svg>
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", default=os.environ.get("GH_USER", "aasif-md1")); ap.add_argument("--out", default="assets/snake.svg")
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
