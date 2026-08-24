"""Install the sandbox into the personal-website repo.

Copies the route's files and registers the route in the site's `site.json`, then
lets the site's own `tools/gen_config.py` regenerate `_headers` and `sitemap.xml`.

This used to hand-patch those two files. It no longer does, and it must not: the
site now generates them from `site.json`, so a script that edited the outputs
directly would be overwritten on the next generate -- or worse, would silently
disagree with it. One source of truth.

Every step is idempotent -- running twice changes nothing the second time -- and
`--dry-run` reports the plan without writing. It deliberately does NOT touch
`index.html` or `projects.html`: where this appears in the portfolio narrative is
an editorial decision, not something a script should make. It does not commit or
push either.

Usage (from the agent_medicine project root):
    python tools/install_to_site.py --dry-run
    python tools/install_to_site.py
    python tools/install_to_site.py --target <path-to-site-copy>
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
WEB = os.path.join(PROJECT_ROOT, "web")
DEFAULT_TARGET = os.path.join(os.path.dirname(PROJECT_ROOT), "personal_website")

ROUTE = "clinical-agent"
CSS_FILES = ["agent.css", "agent-lesson.css", "agent-panel.css", "agent-trace.css"]
PAGE_FILES = ["clinical-agent.html", *CSS_FILES]
ASSET_FILES = [
    "ca-actions.js", "ca-agents.js", "ca-app.js", "ca-cases.js",
    "ca-lesson-view.js", "ca-lessons.js", "ca-policy.js", "ca-render.js",
    "ca-runtime.js", "ca-scoring.js",
    # Evidence image for the homepage feature card and the Open Graph preview.
    # Regenerate with tools/make_feature_image.py.
    "clinical-agent-project.webp",
]

# The CSP itself is no longer spelled out here. The route asks for scripts via
# `"scripts": true` in site.json and the site's generator builds the policy, so
# there is exactly one copy of the directive list in the repo.
LASTMOD = "2026-08-06"


def copy_files(target: str, dry_run: bool) -> list[str]:
    actions = []
    for name in PAGE_FILES:
        src, dst = os.path.join(WEB, name), os.path.join(target, name)
        actions.append(f"copy  {name}")
        if not dry_run:
            shutil.copyfile(src, dst)
    assets_dir = os.path.join(target, "assets")
    if not dry_run:
        os.makedirs(assets_dir, exist_ok=True)
    for name in ASSET_FILES:
        src, dst = os.path.join(WEB, "assets", name), os.path.join(assets_dir, name)
        actions.append(f"copy  assets/{name}")
        if not dry_run:
            shutil.copyfile(src, dst)
    return actions


def register_route(target: str, dry_run: bool) -> list[str]:
    """Add the route to site.json. The site generates its own config from it.

    The stylesheet cache entries are NOT registered here: gen_config.py reads the
    stylesheets off the filesystem, so copying the files is enough.
    """
    path = os.path.join(target, "site.json")
    manifest = json.load(open(path, encoding="utf-8"))
    actions = []
    match = f"/{ROUTE}*"
    loc = f"/{ROUTE}"

    if any(r.get("match") == match for r in manifest["routes"]):
        actions.append(f"skip  site.json: route {match} already registered")
    else:
        manifest["routes"].append(
            {"match": match, "loc": loc, "lastmod": LASTMOD, "scripts": True}
        )
        actions.append(f"patch site.json: registered {match} with scripts: true")

    order = manifest.setdefault("sitemap_order", [])
    if loc in order:
        actions.append(f"skip  site.json: {loc} already in sitemap_order")
    else:
        order.append(loc)
        actions.append(f"patch site.json: appended {loc} to sitemap_order")

    if not dry_run and any(a.startswith("patch") for a in actions):
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=True)
            fh.write("\n")
    return actions


def regenerate_config(target: str, dry_run: bool) -> list[str]:
    """Hand off to the site's own generator rather than editing its outputs."""
    generator = os.path.join(target, "tools", "gen_config.py")
    if not os.path.exists(generator):
        return [f"WARN  {generator} missing; _headers and sitemap.xml were NOT updated"]
    if dry_run:
        return ["would run tools/gen_config.py to regenerate _headers and sitemap.xml"]
    proc = subprocess.run(
        [sys.executable, os.path.join("tools", "gen_config.py")],
        cwd=target, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"gen_config.py failed:\n{proc.stdout}\n{proc.stderr}")
    wrote = [ln.strip() for ln in proc.stdout.splitlines() if ln.startswith("wrote ")]
    return [f"gen_config: {w}" for w in wrote] or ["gen_config: already up to date"]


def main() -> None:
    ap = argparse.ArgumentParser(description="Install the clinical-agent route into the site.")
    ap.add_argument("--target", default=DEFAULT_TARGET, help="path to the personal_website repo")
    ap.add_argument("--dry-run", action="store_true", help="report the plan, write nothing")
    args = ap.parse_args()

    target = os.path.abspath(args.target)
    for required in ("_headers", "sitemap.xml", "base.css", "site.json"):
        if not os.path.exists(os.path.join(target, required)):
            raise SystemExit(f"{target} does not look like the site repo (missing {required})")

    actions = []
    actions += copy_files(target, args.dry_run)
    actions += register_route(target, args.dry_run)
    actions += regenerate_config(target, args.dry_run)

    print(f"{'DRY RUN -- ' if args.dry_run else ''}target: {target}\n")
    for action in actions:
        print(f"  {action}")
    print(f"\n{len(actions)} action(s).")
    if args.dry_run:
        print("Nothing was written.")
        return
    print(
        "\nNot done automatically, on purpose:\n"
        f"  - link /{ROUTE} from index.html or projects.html (editorial decision)\n"
        "  - review, commit and push from the site repo (outward-facing action)\n"
        f"\nPreview:  python -m http.server 4173 --bind 127.0.0.1   (in {target})\n"
        f"          then open http://127.0.0.1:4173/{ROUTE}.html"
    )


if __name__ == "__main__":
    main()
