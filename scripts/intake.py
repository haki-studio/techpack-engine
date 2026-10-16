#!/usr/bin/env python3
"""Inbox -> projects. Used by the /techpack command.

  intake.py sheet                 contact sheet of every image in inbox/ (with a 100 px grid) -> inbox/_contact.png
  intake.py crop SRC x0 y0 x1 y1 OUT   crop a region (pixel coords of SRC) to OUT
  intake.py apply PLAN.json       create projects/<slug>/ for every product in the plan, copy/crop its images into
                                  inputs/, write brief.md + STATUS.json, move used inbox files to inbox/_done/
Plan format: {"products": [{"slug", "name", "garment", "block", "process", "elements": [...], "ip_flags": [...],
              "assumptions": [...], "images": [{"src", "crop": [x0,y0,x1,y1] | null, "as": "front_back.png"}]}]}
"""
import sys, os, json, shutil, glob, datetime
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(ROOT, "inbox")
IMG = (".png", ".jpg", ".jpeg", ".webp")

def inbox_images():
    return sorted(p for p in glob.glob(os.path.join(INBOX, "*")) if p.lower().endswith(IMG) and not os.path.basename(p).startswith("_"))

def sheet():
    ims = inbox_images()
    if not ims: print("inbox is empty"); return
    tiles = []
    for p in ims:
        im = Image.open(p).convert("RGB"); W, H = im.size
        d = ImageDraw.Draw(im)
        for x in range(0, W, 100): d.line([(x, 0), (x, H)], fill=(255, 0, 0), width=1); d.text((x + 2, 2), str(x), fill=(255, 0, 0))
        for y in range(0, H, 100): d.line([(0, y), (W, y)], fill=(255, 0, 0), width=1); d.text((2, y + 2), str(y), fill=(255, 0, 0))
        tiles.append((os.path.basename(p), im))
        print(f"{os.path.basename(p)}  {W}x{H}")
        im.save(os.path.join(INBOX, f"_grid_{os.path.splitext(os.path.basename(p))[0]}.png"))
    print("grid overlays written to inbox/_grid_*.png (view them to read crop coordinates)")

def crop(src, x0, y0, x1, y1, out):
    im = Image.open(src); im.crop((int(x0), int(y0), int(x1), int(y1))).save(out); print("cropped", out)

BRIEF = """# Brief — {name}
_Auto-filled at intake {date}. Edit anything that's wrong; the build reads this file._

- Slug: {slug}
- Garment: {garment}
- Fit block: {block}
- Process: {process}
- Sizes: XS–3XL (default)
- Shell fabric: [proposed — confirm]
- Hardware / trims: [proposed — confirm]
- Factory: 360 × 360 frames, 15-needle heads (default — change if different)

## Elements
{elements}

## IP / licensing flags
{ip}

## Assumptions made at intake
{assumptions}
"""

def apply(plan_path):
    plan = json.load(open(plan_path)); used = set()
    for pr in plan["products"]:
        slug = pr["slug"]; P = os.path.join(ROOT, "projects", slug); I = os.path.join(P, "inputs")
        os.makedirs(I, exist_ok=True)
        for k, im in enumerate(pr.get("images", [])):
            src = os.path.join(ROOT, im["src"]) if not os.path.isabs(im["src"]) else im["src"]
            out = os.path.join(I, im.get("as") or f"mockup_{k+1}.png")
            if im.get("crop"): crop(src, *im["crop"], out)
            else: shutil.copy(src, out)
            used.add(src)
        li = lambda xs, empty: "\n".join(f"- {x}" for x in xs) if xs else f"- {empty}"
        open(os.path.join(I, "brief.md"), "w").write(BRIEF.format(
            name=pr.get("name", slug), slug=slug, date=datetime.date.today().isoformat(), garment=pr.get("garment", "?"),
            block=pr.get("block", "unknown — needs a fit chart"), process=pr.get("process", "embroidery"),
            elements=li(pr.get("elements", []), "to be inventoried"), ip=li(pr.get("ip_flags", []), "none seen"),
            assumptions=li(pr.get("assumptions", []), "none")))
        if not os.path.exists(os.path.join(P, "README.md")):
            open(os.path.join(P, "README.md"), "w").write(f"# {pr.get('name', slug)}\nBuilt by the /techpack command. Inputs + brief in inputs/, outputs in out/.\n")
        os.system(f'python3 "{os.path.join(ROOT, "scripts", "status_set.py")}" {slug} intake "projects created from inbox"')
        print("project", slug)
    done = os.path.join(INBOX, "_done"); os.makedirs(done, exist_ok=True)
    for src in used:
        if src.startswith(INBOX) and os.path.exists(src): shutil.move(src, os.path.join(done, os.path.basename(src)))
    for g in glob.glob(os.path.join(INBOX, "_grid_*.png")): os.remove(g)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sheet"
    if cmd == "sheet": sheet()
    elif cmd == "crop": crop(*sys.argv[2:8])
    elif cmd == "apply": apply(sys.argv[2])
    else: print(__doc__)
