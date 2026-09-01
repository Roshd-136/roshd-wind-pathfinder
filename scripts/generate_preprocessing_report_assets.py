"""
تولید نمودارها و مقایسه دقت IDW/Kriging برای گزارش پیش‌پردازش (گام ۲).

این اسکریپت روی داده واقعی `data/khorasan_wind_qc_cleaned.csv` اجرا می‌شود و:
1. با leave-one-station-out cross-validation، خطای IDW و Kriging را روی
   سرعت باد مقایسه می‌کند (نمودار ستونی خطا).
2. سری زمانی سرعت باد هر سه ایستگاه را رسم می‌کند.
3. یک لحظه‌ی مشخص را با هر دو روش درون‌یابی کرده و میدان درون‌یابی‌شده
   را کنار هم نشان می‌دهد.

خروجی‌ها در `docs/assets/` ذخیره می‌شوند و در `docs/preprocessing_report.md`
استفاده شده‌اند.

اجرا:
    python scripts/generate_preprocessing_report_assets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from preprocessing.idw import IDWInterpolator  # noqa: E402
from preprocessing.kriging import KrigingInterpolator  # noqa: E402

DATA_PATH = ROOT / "data" / "khorasan_wind_qc_cleaned.csv"
ASSETS_DIR = ROOT / "docs" / "assets"


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def leave_one_station_out_errors(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """برای هر رکورد، ایستگاه مربوطه را کنار می‌گذارد و مقدارش را از دو
    ایستگاه دیگر با IDW و Kriging تخمین می‌زند؛ خطای مطلق هر دو روش را
    برمی‌گرداند."""
    stations = list(df["station"].unique())
    coords = df.drop_duplicates("station").set_index("station")[["lat", "lon"]]

    idw_errors, krig_errors = [], []
    for _, group in df.groupby("timestamp"):
        g = group.set_index("station")
        for held_out in stations:
            others = [s for s in stations if s != held_out]
            src_coords = coords.loc[others].values
            src_vals = g.loc[others, "speed"].values
            tgt_coord = coords.loc[[held_out]].values
            true_val = g.loc[held_out, "speed"]

            idw = IDWInterpolator(power=2.0)
            pred_idw = idw.interpolate_scalar(tgt_coord, src_coords, src_vals)[0]
            idw_errors.append(abs(pred_idw - true_val))

            krig = KrigingInterpolator(src_coords, src_vals, variogram_model="spherical", n_lags=2)
            pred_krig = krig.predict(tgt_coord)[0]
            krig_errors.append(abs(pred_krig - true_val))

    return np.array(idw_errors), np.array(krig_errors)


def plot_accuracy_comparison(idw_errors: np.ndarray, krig_errors: np.ndarray) -> None:
    idw_rmse, krig_rmse = np.sqrt(np.mean(idw_errors**2)), np.sqrt(np.mean(krig_errors**2))
    idw_mae, krig_mae = np.mean(idw_errors), np.mean(krig_errors)

    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(2)
    w = 0.35
    ax.bar(x - w / 2, [idw_rmse, krig_rmse], w, label="RMSE (m/s)", color="#4C72B0")
    ax.bar(x + w / 2, [idw_mae, krig_mae], w, label="MAE (m/s)", color="#DD8452")
    ax.set_xticks(x)
    ax.set_xticklabels(["IDW", "Kriging"])
    ax.set_ylabel("error (m/s)")
    ax.set_title("IDW vs Kriging accuracy (leave-one-station-out CV, speed)")
    ax.legend()
    for i, v in enumerate([idw_rmse, krig_rmse]):
        ax.text(i - w / 2, v + 0.15, f"{v:.2f}", ha="center", fontsize=9)
    for i, v in enumerate([idw_mae, krig_mae]):
        ax.text(i + w / 2, v + 0.15, f"{v:.2f}", ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(ASSETS_DIR / "idw_vs_kriging_accuracy.png", dpi=140)
    plt.close(fig)


def plot_timeseries(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 4))
    for s in df["station"].unique():
        sub = df[df["station"] == s].sort_values("timestamp")
        ax.plot(sub["timestamp"], sub["speed"], marker="o", markersize=3, label=s)
    ax.set_xlabel("timestamp")
    ax.set_ylabel("wind speed (m/s)")
    ax.set_title("Khorasan station wind speed, 29-30 Aug 2026 (post-QC)")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(ASSETS_DIR / "khorasan_speed_timeseries.png", dpi=140)
    plt.close(fig)


def plot_field_snapshot(df: pd.DataFrame) -> None:
    stations = list(df["station"].unique())
    coords = df.drop_duplicates("station").set_index("station")[["lat", "lon"]]
    ts0 = df["timestamp"].min()
    snap = df[df["timestamp"] == ts0].set_index("station")
    src_coords = coords.loc[stations].values
    src_vals = snap.loc[stations, "speed"].values

    lat_grid = np.linspace(coords["lat"].min() - 0.1, coords["lat"].max() + 0.1, 40)
    lon_grid = np.linspace(coords["lon"].min() - 0.3, coords["lon"].max() + 0.3, 40)
    lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
    target = np.column_stack([lat_mesh.ravel(), lon_mesh.ravel()])

    idw = IDWInterpolator(power=2.0)
    idw_field = idw.interpolate_scalar(target, src_coords, src_vals).reshape(lat_mesh.shape)

    krig = KrigingInterpolator(src_coords, src_vals, variogram_model="spherical", n_lags=2)
    krig_field = krig.predict(target).reshape(lat_mesh.shape)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    fig.suptitle(f"Interpolated wind speed field, {ts0}")
    im = None
    for ax, field, title in zip(axes, [idw_field, krig_field], ["IDW", "Kriging"], strict=True):
        im = ax.pcolormesh(lon_mesh, lat_mesh, field, shading="auto", cmap="viridis")
        ax.scatter(coords["lon"], coords["lat"], c="red", edgecolor="white", s=50, zorder=5)
        for s in stations:
            ax.annotate(
                s, (coords.loc[s, "lon"], coords.loc[s, "lat"]),
                color="white", fontsize=8, xytext=(3, 3), textcoords="offset points",
            )
        ax.set_title(title)
        ax.set_xlabel("lon")
    fig.subplots_adjust(top=0.85, wspace=0.15)
    fig.colorbar(im, ax=axes, label="wind speed (m/s)", shrink=0.85)
    axes[0].set_ylabel("lat")
    fig.savefig(ASSETS_DIR / "idw_kriging_field_snapshot.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data()

    idw_errors, krig_errors = leave_one_station_out_errors(df)
    print(f"IDW  RMSE={np.sqrt(np.mean(idw_errors**2)):.3f}  MAE={np.mean(idw_errors):.3f}")
    print(f"Kriging RMSE={np.sqrt(np.mean(krig_errors**2)):.3f}  MAE={np.mean(krig_errors):.3f}")

    plot_accuracy_comparison(idw_errors, krig_errors)
    plot_timeseries(df)
    plot_field_snapshot(df)
    print(f"Charts written to {ASSETS_DIR}")


if __name__ == "__main__":
    main()
