"""Visualization multi-layer wind graph with REAL Khorasan data.

Renders 2x2: layer graphs (500m & 2000m) with optimal path Mashhad→Neyshabur,
travel-time bar comparison across all 4 layers, and comparison table.

Usage:
    python scripts/visualize_multi_layer_graph.py
Output:
    docs/assets/multi_layer_graph_visualization.png
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.font_manager as fm  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from pathfinding.graph import MultiLayerWindGraph  # noqa: E402
from pathfinding.routing import WindRouter  # noqa: E402

# Persian font with Latin fallback
try:
    fm.fontManager.addfont("/usr/share/fonts/noto/NotoSansArabic-Regular.ttf")
    plt.rcParams["font.family"] = ["Noto Sans Arabic", "DejaVu Sans"]
except (FileNotFoundError, OSError):
    pass
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "khorasan_multi_layer_raw.csv"
OUTPUT_FILE = ROOT / "docs" / "assets" / "multi_layer_graph_visualization.png"

ORIGIN = (36.297, 59.606)  # مشهد
DEST = (36.213, 58.795)  # نیشابور

# نمایش فقط این دو لایه در پنل‌های گراف (مقایسه در نمودار میلهای: هر ۴ لایه)
PANEL_LAYERS = [500.0, 2000.0]


def _draw_layer(ax: plt.Axes, graph, result, title: str) -> None:
    """Draw one layer's graph + optimal path."""
    for (fid, tid), edge in graph._edges.items():
        fn = graph.get_node(fid)
        tn = graph.get_node(tid)
        if fn is None or tn is None:
            continue
        if math.isinf(edge.weight):
            color, width, alpha = "#999999", 0.6, 0.5
        else:
            width = min(0.4 + edge.weight * 8, 3.0)
            color, alpha = "#999999", 0.55
        ax.plot(
            [fn.lon, tn.lon],
            [fn.lat, tn.lat],
            color=color,
            linewidth=width,
            alpha=alpha,
        )

    for _nid, node in graph.nodes.items():
        ax.plot(node.lon, node.lat, "o", color="#337ab7", markersize=9, zorder=3)

    if result.path:
        lons = [p[1] for p in result.path]
        lats = [p[0] for p in result.path]
        ax.plot(
            lons,
            lats,
            color="#d9534f",
            linewidth=3.0,
            marker="o",
            markersize=7,
            zorder=4,
            label="مسیر بهینه",
        )

    ax.plot(ORIGIN[1], ORIGIN[0], "s", color="#5cb85c", markersize=12, zorder=5)
    ax.plot(DEST[1], DEST[0], "^", color="#f0ad4e", markersize=12, zorder=5)

    ax.set_title(title)
    ax.set_xlabel("طول جغرافیایی")
    ax.set_ylabel("عرض جغرافیایی")
    ax.grid(alpha=0.2)
    ax.legend(loc="best", fontsize=8)


def main() -> None:
    """Build 2x2 visualization from REAL Khorasan multi-layer data."""
    df = pd.read_csv(DATA_FILE)
    mg = MultiLayerWindGraph.build_from_dataframe(df)
    router = WindRouter(mg, criterion="time")
    comp = router.compare_layers(ORIGIN, DEST)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # پنل‌های گراف: دو لایه نمایشی
    for idx, alt in enumerate(PANEL_LAYERS):
        ax = axes[0][idx]
        graph = mg.get_layer(alt)
        title = f"لایه {alt:.0f} متر — مشهد ← نیشابور"
        result = comp.results[alt]
        _draw_layer(ax, graph, result, title)

    # نمودار میلهای: مقایسه زمان سفر هر ۴ لایه
    ax3 = axes[1][0]
    alts = sorted(comp.results.keys())
    times = [comp.results[a].total_cost for a in alts]
    colors = ["#5cb85c" if a == comp.best_altitude else "#d9534f" for a in alts]
    bars = ax3.bar([f"{a:.0f}م" for a in alts], times, color=colors)
    ax3.set_title("مقایسه زمان سفر مشهد ← نیشابور در ۴ لایه")
    ax3.set_ylabel("زمان (ساعت)")
    ax3.grid(axis="y", alpha=0.3)
    for bar, t in zip(bars, times, strict=True):
        ax3.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{t:.4f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    # جدول مقایسه
    ax4 = axes[1][1]
    ax4.axis("off")
    table_data = [["لایه (م)", "باد میانگین (م/ث)", "مسافت (km)", "زمان (ساعت)", "بهترین؟"]]
    for a in alts:
        r = comp.results[a]
        layer_df = df[df["altitude"] == a]
        avg_speed = layer_df["wind_speed"].mean()
        table_data.append(
            [
                f"{a:.0f}",
                f"{avg_speed:.1f}",
                f"{r.total_distance_km:.2f}",
                f"{r.total_cost:.4f}",
                "✅" if a == comp.best_altitude else "—",
            ]
        )
    table = ax4.table(
        cellText=table_data,
        loc="center",
        colWidths=[0.22, 0.30, 0.20, 0.20, 0.16],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.4)
    for (row, _col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#5cb85c")
            cell.set_text_props(color="white", fontweight="bold")
    ax4.set_title("جدول مقایسه لایه‌ها — داده واقعی Khorasan")

    fig.suptitle(
        "گراف باد چندلایه و مسیر بهینه — داده واقعی Khorasan (Open-Meteo)",
        fontsize=14,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FILE, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"تصویر ذخیره شد: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
