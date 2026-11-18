"""
OsdagBridge report — charts generated at report time (matplotlib, headless).

* utilization_chart()  : Utilization Ratio (UR = Demand / Capacity) per check,
                         one panel per primary element, red dashed UR = 1.0 line.
* material_chart()     : steel tonnage per component, concrete volume vs
                         reinforcement weight.

Colours / fonts come from styles.py so the charts match the PDF palette.
Both functions return the written PNG path, or None if there is no data.
"""
import os
import re

# Object-oriented matplotlib only (Figure + Agg canvas). We deliberately do NOT
# import pyplot or call matplotlib.use(): the desktop app already uses the Qt
# backend for its interactive plots, and switching backends globally from the
# report thread would break them. A standalone Figure is also thread-safe.
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from osdagbridge.core.reports import styles as S

UR_LIMIT = 1.0
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.grid(axis="y", linestyle=":", linewidth=0.6, alpha=0.6)
    ax.set_axisbelow(True)


def parse_number(cell):
    """First number in a LaTeX table cell ('\\textcolor{red}{1.58}' -> 1.58), else None."""
    m = _NUM.search(str(cell or "")) if cell not in (None, "---", "N/A") else None
    return float(m.group()) if m else None


# =============================================================================
# 1. Utilization ratio chart (Section 5.5)
# =============================================================================
def utilization_chart(groups, out_path):
    """
    groups: {element name: [(check label, UR float or None), ...], ...}
            e.g. {"Steel Plate Girders": [("Moment", 0.20), ("Fatigue", 1.58)], ...}
    Writes a 2x2 panel bar chart to out_path.
    """
    if not any(ur is not None for checks in groups.values() for _, ur in checks):
        return None
    names = list(groups)
    ncols = 2
    nrows = (len(names) + 1) // 2
    fig = Figure(figsize=(7.2, 3.1 * nrows))
    FigureCanvasAgg(fig)
    axes = fig.subplots(nrows, ncols, squeeze=False)
    ymax = max([UR_LIMIT] + [ur for c in groups.values() for _, ur in c if ur is not None]) * 1.18

    for ax, name in zip(axes.flat, names):
        data = [(lbl, ur) for lbl, ur in groups[name] if ur is not None]
        _style_axes(ax)
        ax.set_title(name, fontsize=9.5, fontweight="bold")
        ax.set_ylim(0, ymax)
        ax.axhline(UR_LIMIT, color=S.hex_color("failRed"), linestyle="--", linewidth=1.2,
                   label="UR = 1.0 (limit)")
        if not data:
            ax.text(0.5, 0.5, "No utilization data available", ha="center", va="center",
                    transform=ax.transAxes, fontsize=8, color="gray")
            ax.set_xticks([])
            continue
        labels, urs = zip(*data)
        colors = [S.hex_color("failRed") if u > UR_LIMIT else S.hex_color("osdagGreen") for u in urs]
        x = range(len(urs))
        ax.bar(x, urs, color=colors, width=0.62, edgecolor="black", linewidth=0.4)
        for xi, u in zip(x, urs):
            # keep labels clear of the dashed limit line
            y_lbl = max(u, UR_LIMIT) + ymax * 0.015 if abs(u - UR_LIMIT) < 0.1 * ymax else u + ymax * 0.015
            ax.text(xi, y_lbl, f"{u:.2f}", ha="center", va="bottom", fontsize=7,
                    color=S.hex_color("failRed") if u > UR_LIMIT else "black",
                    fontweight="bold" if u > UR_LIMIT else "normal")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=7.5)
        ax.set_ylabel("Utilization Ratio (UR)", fontsize=8)

    for ax in list(axes.flat)[len(names):]:
        ax.set_visible(False)

    handles = [
        Rectangle((0, 0), 1, 1, fc=S.hex_color("osdagGreen"), ec="black", lw=0.4),
        Rectangle((0, 0), 1, 1, fc=S.hex_color("failRed"), ec="black", lw=0.4),
        Line2D([0], [0], color=S.hex_color("failRed"), linestyle="--", lw=1.2),
    ]
    fig.legend(handles, ["Pass (UR $\\leq$ 1.0)", "Fail (UR > 1.0)", "Limit UR = 1.0"],
               loc="lower center", ncol=3, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=200)
    return out_path


# =============================================================================
# 2. Material quantity chart (Chapter 7)
# =============================================================================
def material_chart(steel_items, concrete_m3, rebar_mt, out_path, note=None):
    """
    steel_items : [(component, tonnes or None), ...] e.g. [("Girders", 32.89), ...]
    note        : optional footnote under panel (a), e.g. what is not itemised
    concrete_m3 : deck concrete volume (m^3) or None
    rebar_mt    : reinforcement weight (MT) or None
    """
    steel = [(n, v) for n, v in steel_items if v is not None]
    if not steel and concrete_m3 is None and rebar_mt is None:
        return None
    fig = Figure(figsize=(7.2, 3.0))
    FigureCanvasAgg(fig)
    ax1, ax2 = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1.25, 1]})

    # (a) structural steel tonnage per component
    _style_axes(ax1)
    ax1.set_title("(a) Structural Steel Tonnage", fontsize=9.5, fontweight="bold")
    if steel:
        names, vals = zip(*steel)
        bars = ax1.bar(names, vals, color=S.hex_color("osdagGreen"), edgecolor="black", linewidth=0.4, width=0.55)
        top = max(vals)
        for b, v in zip(bars, vals):
            ax1.text(b.get_x() + b.get_width() / 2, v + top * 0.02, f"{v:.2f} t", ha="center", va="bottom", fontsize=7.5)
        ax1.set_ylim(0, top * 1.2)
        total = sum(vals)
        ax1.text(0.98, 0.95, f"Total = {total:.2f} t", transform=ax1.transAxes, ha="right", va="top", fontsize=8,
                 bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=S.hex_color("osdagGreen")))
    ax1.set_ylabel("Weight (MT)", fontsize=8)
    ax1.tick_params(axis="x", labelsize=7.5)
    if note:
        ax1.text(0.0, -0.2, note, transform=ax1.transAxes, fontsize=6.8, style="italic", color="#555555", va="top")

    # (b) concrete volume vs reinforcement weight — different units, so two y-axes
    ax2.set_title("(b) Deck Concrete vs Reinforcement", fontsize=9.5, fontweight="bold")
    ax2.spines["top"].set_visible(False)
    ax2.tick_params(labelsize=8)
    ax2b = ax2.twinx()
    ax2b.spines["top"].set_visible(False)
    ax2b.tick_params(labelsize=8)
    if concrete_m3 is not None:
        ax2.bar([0], [concrete_m3], color=S.hex_color("concreteGray"), edgecolor="black", linewidth=0.4, width=0.5)
        ax2.text(0, concrete_m3 * 1.02, f"{concrete_m3:.2f} m$^3$", ha="center", va="bottom", fontsize=7.5)
        ax2.set_ylim(0, concrete_m3 * 1.22)
    if rebar_mt is not None:
        ax2b.bar([1], [rebar_mt], color=S.hex_color("steelBlue"), edgecolor="black", linewidth=0.4, width=0.5)
        ax2b.text(1, rebar_mt * 1.02, f"{rebar_mt:.2f} t", ha="center", va="bottom", fontsize=7.5)
        ax2b.set_ylim(0, rebar_mt * 1.22)
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["Concrete\n(volume)", "Reinforcement\n(weight)"], fontsize=7.5)
    ax2.set_ylabel("Concrete Volume (m$^3$)", fontsize=8, color=S.hex_color("concreteGray"))
    ax2b.set_ylabel("Reinforcement Weight (MT)", fontsize=8, color=S.hex_color("steelBlue"))
    ax2.tick_params(axis="y", colors=S.hex_color("concreteGray"))
    ax2b.tick_params(axis="y", colors=S.hex_color("steelBlue"))

    fig.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=200)
    return out_path


def figure_tex(path, caption, label, width=r"\textwidth"):
    """Numbered LaTeX figure for a generated chart (empty string if no chart)."""
    if not path:
        return ""
    p = path.replace("\\", "/")
    return "\n".join([
        r"\begin{figure}[H]", r"\centering",
        rf"\includegraphics[width={width}]{{{p}}}",
        rf"\caption{{{caption}}}", rf"\label{{{label}}}",
        r"\end{figure}",
    ])
