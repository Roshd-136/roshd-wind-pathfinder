"""تولید تصویرسازی گراف باد چندلایه و مسیر بهینه.

خروجی: docs/assets/multi_layer_graph_visualization.png
اجرا: python scripts/visualize_multi_layer_graph.py
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

# فونت فارسی با fallback برای گلیف‌های لاتین
try:
    fm.fontManager.addfont("/usr/share/fonts/noto/NotoSansArabic-Regular.ttf")
    plt.rcParams["font.family"] = ["Noto Sans Arabic", "DejaVu Sans"]
except (FileNotFoundError, OSError):
    pass
plt.rcParams["axes.unicode_minus"] = False

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "assets"
OUTPUT_FILE = OUTPUT_PATH / "multi_layer_graph_visualization.png"


def _draw_layer(
    ax: plt.Axes,
    graph,
    result,
    title: str,
) -> None:
    """رسم گراف یک لایه + مسیر بهینه روی آن."""
    # یال‌ها
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

    # گره‌ها
    for _nid, node in graph.nodes.items():
        ax.plot(node.lon, node.lat, "o", color="#337ab7", markersize=9, zorder=3)

    # مسیر بهینه
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

    # مبدأ و مقصد
    ax.plot(origin[1], origin[0], "s", color="#5cb85c", markersize=12, zorder=5)
    ax.plot(dest[1], dest[0], "^", color="#f0ad4e", markersize=12, zorder=5)

    ax.set_title(title)
    ax.set_xlabel("طول جغرافیایی")
    ax.set_ylabel("عرض جغرافیایی")
    ax.grid(alpha=0.2)
    ax.legend(loc="best", fontsize=8)


origin = (36.00, 58.00)
dest = (36.00, 58.30)


def main() -> None:
    """ساخت تصویرسازی ۲×۲: گراف‌ها + مسیر بهینه."""
    # --- داده چندلایه: باد متفاوت → مسیرهای متفاوت در لایه‌ها ---
    # شبکه ۶ نقطه‌ای با گره‌های انحرافی در شمال خط مستقیم A→D:
    # لایه ۵۰۰م: باد ۵۰ م/ث از شمال — باد جانبی مسیر مستقیم A→D را
    #   گران/غیرممکن می‌کند → مسیر بهینه از گره‌های شمالی می‌گذرد (خمیده)
    # لایه ۱۰۰۰م: باد ملایم ۵ م/ث — مسیر مستقیم A→D بهترین است
    pts = [
        (36.00, 58.00),   # A مبدأ
        (36.15, 58.06),   # N1 انحراف شمالی
        (36.18, 58.12),   # N2 انحراف شمالی
        (36.15, 58.20),   # N3 انحراف شمالی
        (36.10, 58.26),   # N4 انحراف شمالی
        (36.00, 58.30),   # D مقصد
    ]
    rows = []
    for lat, lon in pts:
        rows.append(
            {
                "altitude": 500.0,
                "lat": lat,
                "lon": lon,
                "wind_speed": 50.0,
                "wind_direction": 0.0,
            }
        )
    for lat, lon in pts:
        rows.append(
            {
                "altitude": 1000.0,
                "lat": lat,
                "lon": lon,
                "wind_speed": 5.0,
                "wind_direction": 180.0,
            }
        )
    df = pd.DataFrame(rows)

    multi = MultiLayerWindGraph.build_from_dataframe(df, max_edge_distance_km=300.0)
    router = WindRouter(multi, criterion="time")

    comp = router.compare_layers(origin, dest)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # --- ۱و۲) گراف هر لایه ---
    for idx, alt in enumerate(multi.available_layers):
        ax = axes[0][idx]
        graph = multi.get_layer(alt)
        _draw_layer(ax, graph, comp.results[alt], title=f"لایه {alt:.0f} متر")

    # --- ۳) مقایسه زمان سفر ---
    ax3 = axes[1][0]
    alts = sorted(comp.results.keys())
    times = [comp.results[a].total_cost for a in alts]
    bars = ax3.bar(
        [f"{a:.0f}m" for a in alts],
        times,
        color=["#d9534f" if a != comp.best_altitude else "#5cb85c" for a in alts],
    )
    ax3.set_title("مقایسه زمان سفر بین لایه‌ها")
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

    # --- ۴) جدول مقایسه ---
    ax4 = axes[1][1]
    ax4.axis("off")
    table_data = [
        ["لایه (م)", "باد (م/ث)", "مسافت (km)", "زمان (ساعت)", "بهترین؟"]
    ]
    for a in alts:
        r = comp.results[a]
        speed = "۵۰" if a == 500.0 else "۵"
        table_data.append(
            [
                f"{a:.0f}",
                speed,
                f"{r.total_distance_km:.2f}",
                f"{r.total_cost:.4f}",
                "✅" if a == comp.best_altitude else "✔",
            ]
        )
    table = ax4.table(
        cellText=table_data,
        loc="center",
        colWidths=[0.24, 0.24, 0.24, 0.26, 0.18],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.4)
    for (row, _col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#5cb85c")
            cell.set_text_props(color="white", fontweight="bold")
    ax4.set_title("جدول مقایسه لایه‌ها")

    fig.suptitle(
        "گراف باد چندلایه و مسیر بهینه — Roshd Wind Pathfinder",
        fontsize=14,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FILE, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"تصویر ذخیره شد: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
