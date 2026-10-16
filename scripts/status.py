#!/usr/bin/env python3
"""Progress of every product: terminal table + status.html (open in a browser; refreshes itself every 15 s).
  status.py            print once and write status.html
  status.py --watch    refresh every 15 s"""
import os, sys, json, glob, time, html, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES = ["intake", "inventory", "pattern", "art", "stitch", "qa", "documents", "delivered", "review", "reviewed"]

def load():
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "projects", "*", "STATUS.json"))):
        try: out.append(json.load(open(p)))
        except Exception: pass
    return out

def table(rows):
    lines = [f"{'product':32s} {'stage':11s} {'progress':10s} {'updated':20s} note"]
    for s in rows:
        i = s.get("stage_index", 0); bar = "█" * (i + 1) + "·" * (len(STAGES) - i - 1)
        flag = " BLOCKED" if s.get("blocked") else (f" ({len(s.get('questions', []))} q)" if s.get("questions") else "")
        note = (s["log"][-1][2] if s.get("log") else "")[:70]
        lines.append(f"{s['slug'][:32]:32s} {s.get('stage', '?'):11s} {bar:10s} {s.get('updated', '')[:19]:20s} {note}{flag}")
    return "\n".join(lines)

def page(rows):
    cards = []
    for s in rows:
        i = s.get("stage_index", 0); slug = s["slug"]
        steps = "".join(f'<span class="st {"done" if k < i else ("cur" if k == i else "")}">{html.escape(n)}</span>' for k, n in enumerate(STAGES))
        img = f'<img src="projects/{slug}/{html.escape(s["preview"])}?t={int(time.time())}">' if s.get("preview") else '<div class="noimg">no preview yet</div>'
        qs = "".join(f"<li>{html.escape(q)}</li>" for q in s.get("questions", []))
        log = "".join(f"<li><b>{html.escape(t[11:16])}</b> {html.escape(st)} — {html.escape(n)}</li>" for t, st, n in reversed(s.get("log", [])[-6:]))
        cards.append(f'''<section class="card{' blocked' if s.get('blocked') else ''}"><h2>{html.escape(slug)}</h2><div class="steps">{steps}</div>
{img}<ul class="log">{log}</ul>{'<h3>Questions for you</h3><ul class="q">' + qs + '</ul>' if qs else ''}</section>''')
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="15"><title>Tech pack runs</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
:root{{--bg:#F6F3EE;--ink:#1A1A1A;--mut:#77706A;--acc:#C2185B;--ok:#2E7D32;--card:#FFF}}
@media (prefers-color-scheme:dark){{:root{{--bg:#141312;--ink:#EEE9E2;--mut:#9C958D;--card:#1F1D1B}}}}
body{{margin:0;padding:24px 16px;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif}}
h1{{font-size:20px;margin:0 0 4px}} .sub{{color:var(--mut);margin-bottom:18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}}
.card{{background:var(--card);border-radius:10px;padding:14px;box-shadow:0 1px 3px #0002}} .card.blocked{{outline:2px solid var(--acc)}}
h2{{font-size:15px;margin:0 0 8px}} h3{{font-size:13px;margin:10px 0 4px;color:var(--acc)}}
.steps{{display:flex;flex-wrap:wrap;gap:3px;margin-bottom:10px}} .st{{font-size:11px;padding:2px 6px;border-radius:9px;background:#8882;color:var(--mut)}}
.st.done{{background:var(--ok);color:#fff}} .st.cur{{background:var(--acc);color:#fff}}
img{{width:100%;border-radius:6px;background:#8881}} .noimg{{height:120px;display:grid;place-items:center;color:var(--mut);background:#8881;border-radius:6px}}
.log,.q{{padding-left:18px;margin:8px 0 0;font-size:12.5px}} .log li{{color:var(--mut)}}
</style></head><body><h1>Tech pack runs</h1><div class="sub">{len(rows)} products · refreshed {datetime.datetime.now():%H:%M:%S} · updates every 15 s</div>
<div class="grid">{"".join(cards)}</div></body></html>'''

def once():
    rows = load(); open(os.path.join(ROOT, "status.html"), "w").write(page(rows)); return table(rows)

if __name__ == "__main__":
    if "--watch" in sys.argv:
        while True:
            t = once(); os.system("clear"); print(t); print(f"\nstatus.html updated {datetime.datetime.now():%H:%M:%S} — Ctrl-C to stop"); time.sleep(15)
    else:
        print(once())
