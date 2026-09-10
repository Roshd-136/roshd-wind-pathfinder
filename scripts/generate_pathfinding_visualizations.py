"""Generate pathfinding visualization assets for the routing task.

Produces images under docs/assets/ using REAL Khorasan station wind data
(data/khorasan_wind_qc_cleaned.csv) and the actual routing pipeline
(pathfinding.graph / pathfinding.routing):

1.  docs/assets/pathfinding_best_layer_map.png
    Depth-map style map: for a dense grid of origin points across the
    Khorasan region, per-altitude IDW wind fields (built from the real
    station speeds/directions scaled by an Ekman-like altitude profile)
    are used to estimate the ground-speed along the direct great-circle
    leg toward Mashhad; the altitude layer with the lowest time cost is
    shown. Color = best layer (terrain colormap), text = layer.

2.  docs/assets/pathfinding_optimized_route.png
    Best (fastest) route Mashhad -> Sabzevar computed by the real
    WindRouter, drawn on top of an IDW wind-speed field with the
    per-layer alternative paths shown faintly.

Run:
    python scripts/generate_pathfinding_visualizations.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as path_effects  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pathfinding.graph import MultiLayerWindGraph, WindGraph  # noqa: E402
from pathfinding.routing import WindRouter  # noqa: E402
from preprocessing.consistency import haversine_km  # noqa: E402
from preprocessing.idw import IDWInterpolator  # noqa: E402

DATA_PATH = ROOT / "data" / "khorasan_wind_qc_cleaned.csv"
ASSETS_DIR = ROOT / "docs" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Khorasan region bounding box (slightly padded around the 3 stations).
LAT_MIN, LAT_MAX = 36.05, 36.45
LON_MIN, LON_MAX = 57.45, 59.85

# Altitude layers: (altitude_m, speed_scale, direction_rotation_deg)
# Ekman-like: speed increases with height, wind direction rotates clockwise.
LAYERS = [
    (500, 1.15, 0),
    (1000, 0.95, 10),
    (1500, 0.90, 25),
    (2000, 1.30, 40),
]

# Airspeed of the (hypothetical) aircraft, m/s.
AIRSPEED_MPS = 20.0

MASHHAD = (36.297, 59.606)
SABZEVAR = (36.215, 57.678)


def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def station_layer_arrays(df: pd.DataFrame) -> dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Return per-altitude (coords, speed, direction) from real stations."""
    stations = df.drop_duplicates("station")
    coords = stations[["lat", "lon"]].to_numpy(dtype=float)
    result: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for alt, scale, rot in LAYERS:
        speed = stations["speed"].to_numpy(dtype=float) * scale
        direction = (stations["direction"].to_numpy(dtype=float) + rot) % 360.0
        result[alt] = (coords, speed, direction)
    return result


def ground_speed(
    wind_speed: np.ndarray | float,
    wind_dir_deg: np.ndarray | float,
    bearing_deg: np.ndarray | float,
    airspeed: float = AIRSPEED_MPS,
) -> np.ndarray | float:
    """Ground speed along a bearing given wind (meteorological direction)."""
    wind_rad = np.deg2rad(wind_dir_deg)
    bearing_rad = np.deg2rad(bearing_deg)
    # wind blowing FROM wind_dir -> velocity TO (wind_dir+180)
    u = wind_speed * np.cos(wind_rad + np.pi)
    v = wind_speed * np.sin(wind_rad + np.pi)
    ua = airspeed * np.sin(bearing_rad)
    va = airspeed * np.cos(bearing_rad)
    return np.hypot(ua + u, va + v)


def compute_best_layer_map(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-altitude IDW fields -> best layer (min time) toward Mashhad."""
    fields = station_layer_arrays(df)
    glats = np.linspace(LAT_MIN, LAT_MAX, 41)
    glons = np.linspace(LON_MIN, LON_MAX, 81)
    GX, GY = np.meshgrid(glons, glats)
    grid = np.stack([GY.ravel(), GX.ravel()], axis=1)

    best = np.full((len(glats), len(glons)), np.nan)
    times: dict[int, np.ndarray] = {}

    for alt, (coords, speed, direction) in fields.items():
        interp = IDWInterpolator(power=2.0)
        sp = interp.interpolate_scalar(grid, coords, speed)
        dr = interp.interpolate_scalar(grid, coords, direction)
        bearing = np.array(
            [
                _bearing(lat, lon, MASHHAD[0], MASHHAD[1])
                for lat, lon in zip(GY.ravel(), GX.ravel(), strict=False)
            ]
        )
        gs = ground_speed(sp, dr, bearing)
        dkm = np.array([haversine_km(lat, lon, MASHHAD[0], MASHHAD[1]) for lat, lon in zip(GY.ravel(), GX.ravel(), strict=False)])
        times[alt] = dkm / (gs / 3.6) / 3600.0

    # argmin across layers
    tstack = np.stack([times[a] for a, _, _ in LAYERS], axis=0)
    best_idx = np.nanargmin(tstack, axis=0)
    best = np.array([LAYERS[i][0] for i in best_idx]).reshape(GX.shape)
    return glats, glons, best


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing (degrees) from point 1 to point 2 (great circle)."""
    phi1, phi2 = np.deg2rad(lat1), np.deg2rad(lat2)
    dlam = np.deg2rad(lon2 - lon1)
    y = np.sin(dlam) * np.cos(phi2)
    x = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlam)
    return np.mod(np.rad2deg(np.arctan2(y, x)), 360.0)


def build_multi_layer(df: pd.DataFrame) -> MultiLayerWindGraph:
    ml = MultiLayerWindGraph()
    for alt, scale, rot in LAYERS:
        d = df.copy()
        d["altitude"] = alt
        d["speed"] = d["speed"] * scale
        d["direction"] = (d["direction"] + rot) % 360.0
        graph = WindGraph.build_from_dataframe(d, altitude=alt, criterion="time")
        ml.add_layer(graph)
    return ml


def plot_best_layer_map(
    lats: np.ndarray,
    lons: np.ndarray,
    best: np.ndarray,
    stations: pd.DataFrame,
    out_path: Path,
) -> None:
    """Depth/height-style map: color = optimal layer altitude."""
    fig, ax = plt.subplots(figsize=(11, 6.5))
    X, Y = np.meshgrid(lons, lats)

    cmap = plt.get_cmap("terrain")
    pcm = ax.pcolormesh(X, Y, best, cmap=cmap, shading="auto", vmin=0, vmax=2200)
    # Contour lines like a depth map
    cs = ax.contour(
        X, Y, best,
        levels=[500, 1000, 1500, 2000],
        colors="black", linewidths=0.6, alpha=0.7,
    )
    ax.clabel(cs, fmt="%d m", fontsize=8)

    # Label each grid cell with best layer (sparse labels to avoid clutter)
    step = 4
    for i in range(0, len(lats), step):
        for j in range(0, len(lons), step):
            v = best[i, j]
            if not np.isnan(v):
                ax.text(
                    lons[j], lats[i], f"{int(v)}",
                    fontsize=6, ha="center", va="center", color="white",
                    path_effects=[path_effects.withStroke(linewidth=1.2, foreground="black")],
                )

    # Stations
    for _, s in stations.iterrows():
        ax.plot(s.lon, s.lat, "k^", markersize=11, zorder=5)
        ax.text(s.lon + 0.03, s.lat + 0.005, s.station, fontsize=9, fontweight="bold", zorder=6)

    ax.plot(MASHHAD[1], MASHHAD[0], "r*", markersize=18, zorder=6)
    ax.text(MASHHAD[1] - 0.15, MASHHAD[0] + 0.015, "هدف: مشهد", fontsize=10, color="red", fontweight="bold")

    ax.set_xlabel("طول جغرافیایی (درجه)")
    ax.set_ylabel("عرض جغرافیایی (درجه)")
    ax.set_title(
        "بهترین لایه ارتفاعی برای رسیدن به مشهد — نقشهٔ عمق لایه‌ها\n"
        "(هر نقطه: لایه‌ای که کمترین زمان سفر را دارد؛ میدان باد per-layer IDW از دادهٔ واقعی)",
        fontsize=12,
    )
    cbar = fig.colorbar(pcm, ax=ax, label="بهترین ارتفاع لایه (متر)", shrink=0.82)
    cbar.set_ticks([500, 1000, 1500, 2000])
    ax.set_xlim(LON_MIN, LON_MAX)
    ax.set_ylim(LAT_MIN, LAT_MAX)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")


def plot_optimized_route(
    ml: MultiLayerWindGraph,
    df: pd.DataFrame,
    out_path: Path,
) -> None:
    """Draw optimized Mashhad->Sabzevar route over IDW wind field."""
    router = WindRouter(ml, criterion="time")
    result = router.find_optimal_path(MASHHAD, SABZEVAR)
    comparison = router.compare_layers(MASHHAD, SABZEVAR)

    # IDW wind field from real station data (mean speed)
    stations = df.drop_duplicates("station")
    coords = stations[["lat", "lon"]].to_numpy(dtype=float)
    speed = stations["speed"].to_numpy(dtype=float)
    interp = IDWInterpolator(power=2.0)
    glats = np.linspace(LAT_MIN, LAT_MAX, 60)
    glons = np.linspace(LON_MIN, LON_MAX, 90)
    GX, GY = np.meshgrid(glons, glats)
    grid = np.stack([GY.ravel(), GX.ravel()], axis=1)
    speed_field = interp.interpolate_scalar(grid, coords, speed).reshape(GX.shape)

    fig, ax = plt.subplots(figsize=(11, 6.5))

    contour = ax.pcolormesh(GX, GY, speed_field, cmap="YlGnBu", shading="auto")
    fig.colorbar(contour, ax=ax, label="سرعت باد (m/s) — IDW", shrink=0.82)

    # Per-layer routes (faint)
    layer_styles = {500: "-", 1000: "--", 1500: "-.", 2000: ":"}
    layer_colors = {500: "#888888", 1000: "#aaaaaa", 1500: "#bbbbbb", 2000: "#999999"}
    for alt, r in sorted(comparison.results.items()):
        xs = [p[1] for p in r.path]
        ys = [p[0] for p in r.path]
        ax.plot(xs, ys, linestyle=layer_styles[alt], color=layer_colors[alt],
                linewidth=1.6, alpha=0.75, zorder=3)
        ax.text(xs[0], ys[0], f"{int(alt)}m", fontsize=8, color=layer_colors[alt])

    # Best route (thick)
    best = comparison.best_result
    xs = [p[1] for p in best.path]
    ys = [p[0] for p in best.path]
    ax.plot(
        xs, ys, "-", color="darkred", linewidth=3.5, zorder=4,
        label=f"مسیر بهینه (بهترین لایه {int(best.layer_altitude)}م)",
    )

    # Edge cost annotations (leg length in km)
    for i in range(len(best.path) - 1):
        p1, p2 = best.path[i], best.path[i + 1]
        mx, my = (p1[1] + p2[1]) / 2, (p1[0] + p2[0]) / 2
        dkm = haversine_km(p1[0], p1[1], p2[0], p2[1])
        ax.annotate(
            f"{dkm:.0f} km",
            xy=(mx, my), xytext=(mx + 0.12, my - 0.03),
            fontsize=8, color="darkred",
            arrowprops=dict(arrowstyle="-", color="darkred", lw=0.5),
        )

    # Stations
    for _, s in stations.iterrows():
        ax.plot(s.lon, s.lat, "k^", markersize=11, zorder=5)
        ax.text(s.lon + 0.03, s.lat + 0.005, s.station, fontsize=9, fontweight="bold", zorder=6)

    ax.plot(MASHHAD[1], MASHHAD[0], "r*", markersize=18, zorder=6)
    ax.plot(SABZEVAR[1], SABZEVAR[0], "g*", markersize=18, zorder=6)
    ax.text(MASHHAD[1] - 0.15, MASHHAD[0] + 0.018, "مبدأ: مشهد", fontsize=9, color="red", fontweight="bold")
    ax.text(SABZEVAR[1] - 0.18, SABZEVAR[0] - 0.03, "مقصد: سبزوار", fontsize=9, color="green", fontweight="bold")

    ax.set_xlabel("طول جغرافیایی (درجه)")
    ax.set_ylabel("عرض جغرافیایی (درجه)")
    ax.set_title(
        f"مسیر بهینهٔ مشهد → سبزوار ({result.total_distance_km:.1f} km، "
        f"~{result.estimated_time_hours:.2f} ساعت)\n"
        f"زمینه: میدان باد IDW — مسیرهای هر لایه به‌صورت کمرنگ",
        fontsize=12,
    )
    ax.legend(loc="lower left")
    ax.set_xlim(LON_MIN, LON_MAX)
    ax.set_ylim(LAT_MIN, LAT_MAX)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved {out_path}")


def main() -> None:
    df = load_data()
    stations = df.drop_duplicates("station")

    lats, lons, best = compute_best_layer_map(df)
    plot_best_layer_map(lats, lons, best, stations, ASSETS_DIR / "pathfinding_best_layer_map.png")

    ml = build_multi_layer(df)
    plot_optimized_route(ml, df, ASSETS_DIR / "pathfinding_optimized_route.png")
    print("\nAll visualizations saved to docs/assets/")


if __name__ == "__main__":
    main()
