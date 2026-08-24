import numpy as np
import pandas as pd


class WindDataQC:

    def __init__(
        self,
        max_speed=75.0,
        min_speed=0.0,
        max_step_speed=15.0,
        flatline_limit=6,
    ):
        self.max_speed = max_speed
        self.min_speed = min_speed
        self.max_step_speed = max_step_speed
        self.flatline_limit = flatline_limit

    def check_range(self, df):
        invalid_speed = (df["wind_speed"] < self.min_speed) | (
            df["wind_speed"] > self.max_speed
        )
        invalid_dir = (df["wind_direction"] < 0) | (df["wind_direction"] > 360)
        return invalid_speed | invalid_dir

    def check_temporal(self, df):
        if df.empty:
            return pd.Series(False, index=df.index)

        speed_diff = df["wind_speed"].diff().abs()
        spike_flag = speed_diff > self.max_step_speed

        group = (df["wind_speed"] != df["wind_speed"].shift()).cumsum()
        flatline_flag = (
            df.groupby(group)["wind_speed"].transform("size")
            >= self.flatline_limit
        )

        return spike_flag | flatline_flag

    def check_spatial(
        self, df, neighbor_col="neighbor_avg_speed", threshold_std=2.5
    ):
        if neighbor_col not in df.columns or df.empty:
            return pd.Series(False, index=df.index)

        std_dev = df[neighbor_col].std()
        if pd.isna(std_dev) or std_dev == 0:
            return pd.Series(False, index=df.index)

        diff = (df["wind_speed"] - df[neighbor_col]).abs()
        return diff > (threshold_std * std_dev)

    def run_qc(self, df):
        df_qc = df.copy()

        flag_range = self.check_range(df_qc)
        flag_temporal = self.check_temporal(df_qc)
        flag_spatial = self.check_spatial(df_qc)

        is_invalid = flag_range | flag_temporal | flag_spatial

        report = {
            "total_records": len(df),
            "range_errors": int(flag_range.sum()),
            "temporal_errors": int(flag_temporal.sum()),
            "spatial_errors": int(flag_spatial.sum()),
            "total_invalid": int(is_invalid.sum()),
        }

        df_cleaned = df_qc[~is_invalid].copy()
        return df_cleaned, report
