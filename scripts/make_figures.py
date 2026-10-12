"""Render the result figures used in README.md and docs/agent_results.md.

    python scripts/make_figures.py

Reads agent/results/combined/summary.json, writes PNGs to docs/img/.
Colors: raw tables = orange, semantic layer = blue (validated categorical pair).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "agent" / "results" / "combined" / "summary.json").read_text(encoding="utf-8"))
OUT = ROOT / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"
RAW, SEM = "#eb6834", "#2a78d6"
for f in font_manager.findSystemFonts():
    if "Inter" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Inter", "DejaVu Sans"], "font.size": 12, "text.color": INK,
                     "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE})


def frame(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0)


def legend(ax, y=1.02):
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="o", ls="", color=RAW, ms=9, label="Raw tables"),
         Line2D([], [], marker="o", ls="", color=SEM, ms=9, label="With semantic layer")]
    ax.legend(handles=h, loc="lower left", bbox_to_anchor=(0, y), ncol=2, frameon=False, fontsize=11,
              handletextpad=0.3, columnspacing=1.4)


# 1. Mean score, raw -> semantic, per model (dumbbell; no zero baseline needed for dots)
fig, ax = plt.subplots(figsize=(7.2, 2.9), dpi=200)
models = [("Claude Haiku 5.5", "haiku"), ("Claude Sonnet 5.5", "sonnet")]
for i, (label, key) in enumerate(models):
    r, s = S["mean_score"][key]["raw"], S["mean_score"][key]["semantic"]
    y = len(models) - 1 - i
    ax.plot([r, s], [y, y], color=GRID, lw=3, solid_capstyle="round", zorder=1)
    ax.scatter([r], [y], s=110, color=RAW, zorder=3, edgecolor=SURFACE, linewidth=2)
    ax.scatter([s], [y], s=110, color=SEM, zorder=3, edgecolor=SURFACE, linewidth=2)
    ax.text(r - 0.006, y, f"{r:.2f}", ha="right", va="center", color=INK2, fontsize=11)
    ax.text(s + 0.006, y, f"{s:.2f}", ha="left", va="center", color=INK, fontsize=11, fontweight="semibold")
ax.set_yticks(range(len(models)), [m for m, _ in reversed(models)], color=INK, fontsize=12)
ax.set_xlim(0.80, 1.0)
ax.set_ylim(-0.6, 1.6)
ax.set_xlabel("Mean score across 6 questions (1.0 = fully correct)", fontsize=10.5)
ax.grid(axis="x", color=GRID, lw=0.8)
ax.set_axisbelow(True)
frame(ax)
legend(ax)
fig.tight_layout()
fig.savefig(OUT / "scores.png")
plt.close(fig)

# 2. Where it mattered: share of runs that found the item
F = S["findings"]
items = [("Stale test after a change control\n(URS-EMS-014, Q1, both models)", F["stale_verification_URS-EMS-014"]),
         ("FMEA rows written as \"TE\" / \"Transduction\nefficiency\" (Q4, Haiku)", F["vocabulary_FM-07_FM-08_haiku_q4"]),
         ("Alarm-system change as shared cause\n(CC-26-011, Q3, both models)", F["ems_cause_CC-26-011_q3"])]
fig, ax = plt.subplots(figsize=(7.2, 3.9), dpi=200)
h = 0.34
for i, (label, d) in enumerate(items):
    y = len(items) - 1 - i
    for off, cond, col in [(h / 2 + 0.02, "raw", RAW), (-h / 2 - 0.02, "semantic", SEM)]:
        k, n = d[cond]
        v = k / n
        ax.barh(y + off, max(v, 0.004), height=h, color=col)
        ax.text(v + 0.015, y + off, f"{k} of {n}", va="center", fontsize=10.5, color=INK2)
ax.set_yticks(range(len(items)), [l for l, _ in reversed(items)], fontsize=10.5, color=INK)
ax.set_xlim(0, 1.12)
ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
ax.set_xlabel("Share of runs whose answer included it", fontsize=10.5)
ax.grid(axis="x", color=GRID, lw=0.8)
ax.set_axisbelow(True)
frame(ax)
legend(ax, y=1.01)
fig.tight_layout()
fig.savefig(OUT / "findings.png")
plt.close(fig)

# 3. Score vs cost per question
C = S["cost_per_run_usd"]
pts = [("Haiku, raw", C["haiku_raw"], S["mean_score"]["haiku"]["raw"], RAW, "o"),
       ("Haiku + semantic", C["haiku_semantic"], S["mean_score"]["haiku"]["semantic"], SEM, "o"),
       ("Sonnet, raw", C["sonnet_raw"], S["mean_score"]["sonnet"]["raw"], RAW, "s"),
       ("Sonnet + semantic", C["sonnet_semantic"], S["mean_score"]["sonnet"]["semantic"], SEM, "s")]
fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=200)
for label, x, y, col, mk in pts:
    ax.scatter([x], [y], s=120, color=col, marker=mk, zorder=3, edgecolor=SURFACE, linewidth=2)
    dx = 1.18 if "Haiku" in label else 0.86
    ax.text(x * dx, y, f"{label}  {y:.2f}", va="center", ha="left" if "Haiku" in label else "right", fontsize=10.5,
            color=INK)
ax.set_xscale("log")
ax.set_xlim(0.007, 0.35)
ax.set_ylim(0.85, 1.0)
ax.set_xticks([0.01, 0.02, 0.05, 0.1, 0.2], ["$0.01", "$0.02", "$0.05", "$0.10", "$0.20"])
ax.minorticks_off()
ax.set_xlabel("Average API cost per question (log scale)", fontsize=10.5)
ax.set_ylabel("Mean score", fontsize=10.5)
ax.grid(color=GRID, lw=0.8)
ax.set_axisbelow(True)
frame(ax)
ax.spines["left"].set_visible(False)
legend(ax)
fig.tight_layout()
fig.savefig(OUT / "cost_vs_score.png")
plt.close(fig)
print("Wrote", ", ".join(p.name for p in sorted(OUT.glob("*.png"))))
