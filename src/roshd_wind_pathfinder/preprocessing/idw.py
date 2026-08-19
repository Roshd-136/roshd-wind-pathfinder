"""
درونیابی وزنی عکس فاصله (Inverse Distance Weighting — IDW)
برای تخمین میدان باد در نقاط فاقد داده مستقیم.
"""

import numpy as np
from numpy.typing import NDArray


class IDWInterpolator:
    """
    پیاده‌سازی الگوریتم IDW با پارامتر توان قابل تنظیم و بهینه‌سازی سرعت.

    فرمول:
        u(x) = Σ (w_i * u_i) / Σ w_i
        w_i = 1 / d(x, x_i)^p

    پارامترها
    ----------
    power : float
        توان فاصله (پیش‌فرض ۲.۰)
    max_points : int | None
        بیشینه تعداد نقاط همسایه برای محاسبه (None = همه نقاط)
    min_distance : float
        حداقل فاصله برای جلوگیری از تقسیم بر صفر
    """

    def __init__(
        self,
        power: float = 2.0,
        max_points: int | None = None,
        min_distance: float = 1e-6,
    ) -> None:
        self.power = float(power)
        self.max_points = max_points
        self.min_distance = float(min_distance)

    def interpolate_scalar(
        self,
        target_points: NDArray[np.float64],
        source_points: NDArray[np.float64],
        source_values: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """
        درونیابی اسکالر با بردارسازی.

        پارامترها
        ----------
        target_points : ndarray, شکل (n_target, 2)
            مختصات نقاط هدف (lat, lon) یا (x, y)
        source_points : ndarray, شکل (n_source, 2)
            مختصات نقاط منبع
        source_values : ndarray, شکل (n_source,)
            مقادیر منبع

        خروجی
        -------
        ndarray, شکل (n_target,)
        """
        target = np.atleast_2d(target_points)
        source = np.atleast_2d(source_points)
        values = np.atleast_1d(source_values)

        n_source = source.shape[0]

        if self.max_points is not None and self.max_points > 0:
            # محدود کردن تعداد نقاط منبع برای سرعت
            n_use = min(self.max_points, n_source)
            source = source[:n_use]
            values = values[:n_use]
            n_source = n_use

        # محاسبه فاصله اقلیدسی: (n_target, n_source)
        diff = target[:, np.newaxis, :] - source[np.newaxis, :, :]
        distances = np.sqrt(np.sum(diff**2, axis=2))

        # جلوگیری از تقسیم بر صفر
        distances = np.clip(distances, self.min_distance, None)

        # وزن‌ها
        weights = 1.0 / (distances**self.power)

        # درونیابی وزنی
        weighted_sum = np.sum(weights * values[np.newaxis, :], axis=1)
        weight_sum = np.sum(weights, axis=1)
        result = weighted_sum / weight_sum

        return result.astype(np.float64)

    def interpolate_wind_field(
        self,
        target_grid: NDArray[np.float64],
        station_coords: NDArray[np.float64],
        u_components: NDArray[np.float64],
        v_components: NDArray[np.float64],
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """
        تخمین میدان باد (u و v) در شبکه نقاط هدف.

        خروجی
        -------
        (u_estimated, v_estimated) : tuple[ndarray, ndarray]
        """
        u_est = self.interpolate_scalar(target_grid, station_coords, u_components)
        v_est = self.interpolate_scalar(target_grid, station_coords, v_components)
        return u_est, v_est
