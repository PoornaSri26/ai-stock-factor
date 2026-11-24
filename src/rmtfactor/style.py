"""Figure tokens for the AI-factor study."""

from __future__ import annotations

TOKENS = {
    "ink": "#111318",
    "grid": "#D6DAE1",
    "bulk": "#9AA3B2",
    "edge": "#B3261E",
    "signal": "#3B6EA5",
    "basket": "#8A5A00",
    "muted": "#6B7280",
}
FIGSIZE = (6.8, 4.2)
DPI = 160


def apply_style() -> None:
    import matplotlib as mpl

    mpl.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": TOKENS["ink"],
            "axes.labelcolor": TOKENS["ink"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": TOKENS["grid"],
            "grid.linewidth": 0.6,
            "grid.alpha": 0.7,
            "text.color": TOKENS["ink"],
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "legend.frameon": False,
            "lines.linewidth": 1.4,
            "savefig.dpi": DPI,
        }
    )
