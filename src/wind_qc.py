"""Wind Data Quality Control Module for AEROPATH."""

from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class QCConfig:
    min_speed: float = 0.0
    max_speed: float = 120.0
    min_direction: float = 0.0
    max_direction: float = 360.0
    outlier_method: str = "zscore"  # "zscore", "iqr", or "mad"
    z_threshold: float = 3.0
    iqr_multiplier: float = 1.5
    max_speed_jump: float = 30.0  # m/s
    max_dir_jump: float = 150.0  # degrees
    spatial_neighbor_radius_deg: float = 0.25
    spatial_z_threshold: float = 3.0
    min_spatial_neighbors: int = 3
    group_cols: List[str] = field(default_factory=lambda: ["lat", "lon"])


class WindQualityControl:
    def __init__(self, config: Optional[QCConfig] = None) -> None:
        self.config = config or QCConfig()

    def _ensure_speed_direction(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if "speed" not in df.columns or "direction" not in df.columns:
            if "u" in df.columns and "v" in df.columns:
                df["speed"] = np.sqrt(df["u"] ** 2 + df["v"] ** 2)
                # Calculate meteorological direction (where wind comes from)
                dir_rad = np.arctan2(-df["u"], -df["v"])
                df["direction"] = (np.degrees(dir_rad) + 360) % 360
            else:
                raise ValueError("DataFrame must contain either ('speed', 'direction') or ('u', 'v').")
        return df

    def run(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        df = self._ensure_speed_direction(df)
        df["qc_flag"] = "VALID"
        df["qc_reasons"] = [[] for _ in range(len(df))]

        total_records = len(df)
        reasons_col = df["qc_reasons"]

        # 1. Missing Values Check
        missing_mask = df["speed"].isna() | df["direction"].isna()
        for idx in df[missing_mask].index:
            reasons_col.loc[idx].append("MISSING_VALUE")

        # 2. Physical Range Check
        range_mask = (
            (df["speed"] < self.config.min_speed)
            | (df["speed"] > self.config.max_speed)
            | (df["direction"] < self.config.min_direction)
            | (df["direction"] > self.config.max_direction)
        )
        for idx in df[range_mask].index:
            reasons_col.loc[idx].append("INVALID_RANGE")

        # 3. Statistical Outlier Check
        if self.config.outlier_method == "zscore":
            mean_sp = df["speed"].mean()
            std_sp = df["speed"].std()
            if std_sp > 0:
                z_scores = np.abs((df["speed"] - mean_sp) / std_sp)
                outlier_mask = z_scores > self.config.z_threshold
                for idx in df[outlier_mask].index:
                    reasons_col.loc[idx].append("STATISTICAL_OUTLIER")

        # 4. Temporal Continuity Check
        if "time" in df.columns:
            df_sorted = df.sort_values(by=self.config.group_cols + ["time"])
            for _, group in df_sorted.groupby(self.config.group_cols):
                if len(group) < 2:
                    continue
                speed_diff = group["speed"].diff().abs()
                dir_diff = group["direction"].diff().abs()
                dir_diff = np.minimum(dir_diff, 360 - dir_diff)

                jump_mask = (speed_diff > self.config.max_speed_jump) | (dir_diff > self.config.max_dir_jump)
                for idx in group[jump_mask].index:
                    reasons_col.loc[idx].append("TEMPORAL_JUMP")

        # 5. Spatial Consistency Check
        if "time" in df.columns and "lat" in df.columns and "lon" in df.columns:
            for _, time_group in df.groupby("time"):
                if len(time_group) <= self.config.min_spatial_neighbors:
                    continue
                coords = time_group[["lat", "lon"]].values
                speeds = time_group["speed"].values
                indices = time_group.index.values

                for i, (idx, (lat, lon), sp) in enumerate(zip(indices, coords, speeds)):
                    dist = np.sqrt((coords[:, 0] - lat) ** 2 + (coords[:, 1] - lon) ** 2)
                    neighbors_mask = (dist <= self.config.spatial_neighbor_radius_deg) & (dist > 0)
                    if np.sum(neighbors_mask) >= self.config.min_spatial_neighbors:
                        neighbor_speeds = speeds[neighbors_mask]
                        n_mean = np.mean(neighbor_speeds)
                        n_std = np.std(neighbor_speeds)
                        if n_std > 0 and np.abs(sp - n_mean) / n_std > self.config.spatial_z_threshold:
                            reasons_col.loc[idx].append("SPATIAL_INCONSISTENCY")

        # Finalize Flags
        invalid_mask = df["qc_reasons"].apply(lambda r: len(r) > 0)
        df.loc[invalid_mask, "qc_flag"] = "INVALID"

        clean_df = df[df["qc_flag"] == "VALID"].copy().drop(columns=["qc_flag", "qc_reasons"])
        removed_df = df[df["qc_flag"] == "INVALID"].copy()

        # Build Report Summary
        error_counts: Dict[str, int] = {}
        for reasons in df["qc_reasons"]:
            for r in reasons:
                error_counts[r] = error_counts.get(r, 0) + 1

        report = {
            "summary": {
                "total_records": total_records,
                "valid_records": len(clean_df),
                "removed_records": len(removed_df),
                "removal_rate_pct": round((len(removed_df) / total_records) * 100, 2) if total_records > 0 else 0,
            },
            "error_counts": error_counts,
            "config": self.config.__dict__,
            "removed_preview": removed_df[["time", "lat", "lon", "speed", "direction", "qc_reasons"]].head(10).to_dict(orient="records") if "time" in df.columns else [],
        }

        return clean_df, report


def report_to_markdown(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    md = [
        "## Wind Data Quality Control Report",
        f"- **Total Records:** {summary['total_records']}",
        f"- **Valid Records:** {summary['valid_records']}",
        f"- **Removed Records:** {summary['removed_records']}",
        f"- **Removal Rate:** {summary['removal_rate_pct']}%",
        "\n### Error Breakdown",
    ]
    for err, count in report["error_counts"].items():
        md.append(f"- **{err}:** {count}")
    return "\n".join(md)


def save_report_json(report: Dict[str, Any], filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
