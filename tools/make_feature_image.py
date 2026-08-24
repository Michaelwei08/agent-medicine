"""Render the portfolio evidence image from the engine's own output.

The homepage feature card and the Open Graph preview both need an image. Rather
than hand-draw one (which could drift from the result it depicts), this runs the
same node harness the parity check uses and plots what it returns.

Palette is taken from the site's base.css tokens so the card sits in the page
rather than on top of it.

Usage (from the agent_medicine project root):
    python tools/make_feature_image.py
"""
from __future__ import annotations

import json
import os
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
OUT_WEBP = os.path.join(PROJECT_ROOT, "web", "assets", "clinical-agent-project.webp")

# base.css tokens.
INK = "#292524"
MUTED = "#78716c"
LINE = "#e7e5e4"
PAPER = "#fafaf9"
TEAL = "#0f766e"
CARDINAL = "#be123c"

LABELS = {
    "keyword": "Keyword filter",
    "mock_model": "Mock model",
    "naive": "Naive",
    "worst_case": "Adversarial",
}

WIDTH, HEIGHT, DPI = 1280, 720, 160


def engine_delta() -> list[dict]:
    proc = subprocess.run(
        ["node", os.path.join("tools", "node_harness.mjs")],
        cwd=PROJECT_ROOT, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"node harness failed:\n{proc.stderr.strip()}")
    return json.loads(proc.stdout)["delta"]


def build(rows: list[dict]) -> None:
    # Ordered benign -> adversarial, drawn top-down in that order.
    rows = list(reversed(rows))
    names = [LABELS.get(r["base"], r["base"]) for r in rows]
    off = [r["unsafe_off"] for r in rows]
    on = [r["unsafe_on"] for r in rows]

    fig, ax = plt.subplots(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)

    y = range(len(rows))
    height = 0.42
    ax.barh([i + height / 2 for i in y], off, height=height,
            color=CARDINAL, label="Guard off", zorder=3)
    ax.barh([i - height / 2 for i in y], on, height=height,
            color=TEAL, label="Guard on", zorder=3)

    for i, value in zip(y, off):
        ax.text(value + 0.012, i + height / 2, f"{value:.3f}", va="center",
                fontsize=9.5, color=CARDINAL, fontweight="bold", zorder=4)
    # The guarded bars are all zero, so they have no length to read. Label the
    # zero explicitly or the strongest result on the chart is invisible.
    for i, value in zip(y, on):
        ax.text(0.012, i - height / 2, f"{value:.3f}", va="center",
                fontsize=9.5, color=TEAL, fontweight="bold", zorder=4)

    ax.set_yticks(list(y))
    ax.set_yticklabels(names, fontsize=11, color=INK)
    # Headroom for the value labels and the legend, without leaving dead space.
    ax.set_xlim(0, max(off) * 1.34)
    ax.set_xlabel("Unsafe-action rate over 14 synthetic cases (lower is safer)",
                  fontsize=9.5, color=MUTED, labelpad=9)
    ax.tick_params(axis="x", colors=MUTED, labelsize=9)
    ax.grid(axis="x", color=LINE, linewidth=0.9, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(LINE)

    # Title lives in figure coordinates, not axes coordinates. As an axes title
    # with loc="left" it inherits the axes width and runs off the right edge.
    fig.text(0.018, 0.945, "Same agent. One toggle.",
             fontsize=17, color=INK, fontweight="600", va="top")
    fig.text(0.018, 0.868, "Enforcement outside the model, not inside it.",
             fontsize=12, color=MUTED, va="top")

    # Top row is the least unsafe, so the upper right is the only clear space.
    ax.legend(loc="upper right", frameon=False, fontsize=10, labelcolor=INK)

    fig.text(0.018, 0.032,
             "Deterministic stand-in agents, synthetic records, self-authored cases. "
             "Research artifact - not a clinical system.",
             fontsize=8, color=MUTED)

    fig.tight_layout(rect=(0.0, 0.055, 1.0, 0.80))
    png = OUT_WEBP.replace(".webp", ".png")
    fig.savefig(png, facecolor=PAPER)
    plt.close(fig)

    img = Image.open(png).convert("RGB").resize((WIDTH, HEIGHT), Image.LANCZOS)
    img.save(OUT_WEBP, "WEBP", quality=90, method=6)
    os.remove(png)

    size = os.path.getsize(OUT_WEBP)
    print(f"wrote {OUT_WEBP}")
    print(f"{img.width}x{img.height}, {size:,} bytes")


if __name__ == "__main__":
    build(engine_delta())
