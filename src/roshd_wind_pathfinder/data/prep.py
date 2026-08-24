import numpy as np
import pandas as pd


class PathfindingDataPrep:

    def __init__(
        self,
        heights=[500, 1000, 1500, 2000],
        grid_resolution=0.1,
        normalize=True,
    ):
        self.heights = heights
        self.grid_resolution = grid_resolution
        self.normalize = normalize

    def convert_units(self, df):
        """تبدیل واحدها و محاسبه بردارهای U و V باد"""
        df_conv = df.copy()

        # تبدیل سرعت به m/s در صورت نیاز
        if "speed_knots" in df_conv.columns:
            df_conv["wind_speed"] = df_conv["speed_knots"] * 0.514444

        # تبدیل جهت باد و سرعت به بردارهای U (شرقی-غربی) و V (شمالی-جنوبی)
        rad = np.radians(df_conv["wind_direction"])
        df_conv["u_component"] = -df_conv["wind_speed"] * np.sin(rad)
        df_conv["v_component"] = -df_conv["wind_speed"] * np.cos(rad)

        return df_conv

    def create_regular_grid(self, df):
        """تبدیل داده‌ها به گرید منظم در ارتفاع‌های مختلف"""
        df_grid = self.convert_units(df)

        # ساخت گرید برای ارتفاعات تعیین شده (500 تا 2000 متر)
        grid_records = []
        lats = np.arange(
            df_grid["latitude"].min(),
            df_grid["latitude"].max() + self.grid_resolution,
            self.grid_resolution,
        )
        lons = np.arange(
            df_grid["longitude"].min(),
            df_grid["longitude"].max() + self.grid_resolution,
            self.grid_resolution,
        )

        for h in self.heights:
            for lat in lats:
                for lon in lons:
                    grid_records.append({
                        "latitude": round(lat, 4),
                        "longitude": round(lon, 4),
                        "altitude": h,
                        "u_component": df_grid["u_component"].mean(),
                        "v_component": df_grid["v_component"].mean(),
                    })

        res_df = pd.DataFrame(grid_records)

        if self.normalize:
            res_df = self.normalize_features(res_df)

        return res_df

    def normalize_features(self, df):
        """نرمال‌سازی مقادیر بردارها بین 0 تا 1"""
        df_norm = df.copy()
        for col in ["u_component", "v_component"]:
            min_val = df_norm[col].min()
            max_val = df_norm[col].max()
            if max_val != min_val:
                df_norm[f"{col}_norm"] = (df_norm[col] - min_val) / (
                    max_val - min_val
                )
            else:
                df_norm[f"{col}_norm"] = 0.0
        return df_norm
