"""
درونیابی Kriging با محاسبه واریوگرام تجربی و برازش مدل.
(.Variogram) برای تخمین دقیق‌تر میدان باد"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# مدل‌های تئوریک واریوگرام
# ---------------------------------------------------------------------------

def _spherical(h: NDArray[np.float64], sill: float, range_: float) -> NDArray[np.float64]:
    """مدل کروی واریوگرام."""
    hr = h / range_
    return np.where(h < range_, sill * (1.5 * hr - 0.5 * hr**3), sill)


def _exponential(h: NDArray[np.float64], sill: float, range_: float) -> NDArray[np.float64]:
    """مدل نمایی واریوگرام."""
    return sill * (1.0 - np.exp(-3.0 * h / range_))


def _gaussian(h: NDArray[np.float64], sill: float, range_: float) -> NDArray[np.float64]:
    """مدل گاوسی واریوگرام."""
    return sill * (1.0 - np.exp(-3.0 * (h / range_) ** 2))


def _linear(h: NDArray[np.float64], sill: float, range_: float) -> NDArray[np.float64]:
    """مدل خطی واریوگرام."""
    return np.clip(sill * h / range_, 0.0, sill)


_VARIOGRAM_MODELS = {
    "spherical": _spherical,
    "exponential": _exponential,
    "gaussian": _gaussian,
    "linear": _linear,
}


@dataclass
class VariogramResult:
    """نتیجه برازش مدل واریوگرام."""

    model_name: str
    sill: float
    range_: float
    nugget: float
    sse: float  # خطای مجموع مربعات


# ---------------------------------------------------------------------------
# محاسبه واریوگرام تجربی
# ---------------------------------------------------------------------------

class EmpiricalVariogram:
    """
    محاسبه واریوگرام تجربی از داده‌های موانع.

    پارامترها
    ----------
    coords : ndarray, شکل (n, 2)
        مختصات نقاط (x, y) یا (lat, lon)
    values : ndarray, شکل (n,)
        مقادیر مشاهده‌شده
    n_lags : int
        تعداد بین‌های (lag bins)
    max_lag : float | None
        حداکثر فاصله لحاظ شود در محاسبه (None = نصف حداکثر فاصله کل)
    """

    def __init__(
        self,
        coords: NDArray[np.float64],
        values: NDArray[np.float64],
        n_lags: int = 20,
        max_lag: float | None = None,
    ) -> None:
        self.coords = np.atleast_2d(np.asarray(coords, dtype=np.float64))
        self.values = np.atleast_1d(np.asarray(values, dtype=np.float64))
        self.n_lags = int(n_lags)

        if max_lag is None:
            from scipy.spatial.distance import pdist
            pairwise = pdist(self.coords)
            max_lag = float(np.percentile(pairwise, 50)) if len(pairwise) > 0 else 1.0
        self.max_lag = float(max_lag)

        self.lag_bins: NDArray[np.float64] = np.zeros(self.n_lags)
        self.semivariance: NDArray[np.float64] = np.zeros(self.n_lags)
        self.counts: NDArray[np.int64] = np.zeros(self.n_lags, dtype=np.int64)
        self.is_computed: bool = False

    # ------------------------------------------------------------------
    def compute(self) -> None:
        """محاسبه واریوگرام تجربی با ساختار بازه‌های یکنواخت (equal-bin)."""
        from scipy.spatial.distance import pdist, squareform

        dist_mat = squareform(pdist(self.coords))
        np.fill_diagonal(dist_mat, np.nan)

        # ماتریس تفاوت جفت‌های دوجمله‌ای
        diff_mat = np.subtract.outer(self.values, self.values) ** 2

        bin_edges = np.linspace(0.0, self.max_lag, self.n_lags + 1)
        lag_centers: list[float] = []
        semi: list[float] = []
        counts: list[int] = []

        for i in range(self.n_lags):
            lo, hi = bin_edges[i], bin_edges[i + 1]
            if i == 0:
                mask = (dist_mat >= lo) & (dist_mat < hi) & (~np.isnan(dist_mat))
            else:
                mask = (dist_mat >= lo) & (dist_mat < hi) & (~np.isnan(dist_mat))

            cnt = int(np.count_nonzero(mask))
            if cnt > 0:
                gamma = 0.5 * np.mean(diff_mat[mask])
                lag_centers.append(float((lo + hi) / 2.0))
                semi.append(float(gamma))
                counts.append(cnt)
            else:
                lag_centers.append(float((lo + hi) / 2.0))
                semi.append(0.0)
                counts.append(0)

        self.lag_bins = np.array(lag_centers, dtype=np.float64)
        self.semivariance = np.array(semi, dtype=np.float64)
        self.counts = np.array(counts, dtype=np.int64)
        self.is_computed = True


# ---------------------------------------------------------------------------
# برازش مدل واریوگرام
# ---------------------------------------------------------------------------

class VariogramFitter:
    """
    برازش مدل‌های تئوریک واریوگرام به داده‌های تجربی با روش حداقل مربعات.

    پارامترها
    ----------
    empirical : EmpiricalVariogram
        شی واریوگرام تجربی محاسبه‌شده
    """

    def __init__(self, empirical: EmpiricalVariogram) -> None:
        self.empirical = empirical

    def fit(self, model_name: str = "spherical") -> VariogramResult:
        """
        برازش مدل مشخص‌شده با استفاده از حداقل مربعات غیرخطی.

        پارامترها
        ----------
        model_name : str
            نام مدل (`spherical`, `exponential`, `gaussian`, `linear`)

        خروجی
        -------
        VariogramResult
            شامل پارامترهای برازش‌شده و خطا
        """
        if not self.empirical.is_computed:
            self.empirical.compute()

        model_fn = _VARIOGRAM_MODELS[model_name]
        lag = self.empirical.lag_bins
        gamma_emp = self.empirical.semivariance

        # فیلتر کردن بین‌های بدون داده
        valid = (gamma_emp > 0) & (self.empirical.counts > 0)
        if np.count_nonzero(valid) < 2:
            return VariogramResult(
                model_name=model_name,
                sill=float(np.nanmax(gamma_emp)) if np.any(valid) else 1.0,
                range_=float(self.empirical.max_lag),
                nugget=0.0,
                sse=0.0,
            )

        h_valid = lag[valid]
        g_valid = gamma_emp[valid]
        sill_init = float(np.max(g_valid))
        range_init = float(np.percentile(h_valid, 75)) if len(h_valid) > 1 else float(self.empirical.max_lag)
        nugget_init = float(np.min(g_valid)) if len(g_valid) > 0 else 0.0

        def _model(h_arr, sill, range_, nugget):
            pred = nugget + model_fn(h_arr, sill - nugget, range_)
            return pred

        def _sse(params):
            sill, range_, nugget = params
            if sill <= nugget or range_ <= 0:
                return 1e20
            pred = _model(h_valid, sill, range_, nugget)
            return float(np.sum((g_valid - pred) ** 2))

        from scipy.optimize import minimize
        initial = [sill_init, range_init, nugget_init]
        result = minimize(_sse, initial, method="Nelder-Mead", options={"maxiter": 5000, "xatol": 1e-6, "fatol": 1e-8})

        sill_fit = float(result.x[0])
        range_fit = float(max(result.x[1], 1e-9))
        nugget_fit = float(max(result.x[2], 0.0))

        if sill_fit < nugget_fit:
            sill_fit = nugget_fit + 1e-6

        final_sse = _sse(result.x)
        return VariogramResult(
            model_name=model_name,
            sill=sill_fit,
            range_=range_fit,
            nugget=nugget_fit,
            sse=final_sse,
        )


# ---------------------------------------------------------------------------
# درونیابی Kriging
# ---------------------------------------------------------------------------

class KrigingInterpolator:
    """
    پیاده‌سازی درونیابی ساده Kriging با استفاده از واریوگرام برازش‌شده.

    این کلاس از مدل واریوگرام برای محاسبه ماتریس کوواریانس بین نقاط منبع
    و به‌واسطه آن، تخمین مقدار در نقاط target محاسبه می‌کند.

    پارامترها
    ----------
    coords : ndarray, شکل (n_source, 2)
        مختصات نقاط منبع (مخاطرات ایستگاه‌های هواشناسی)
    values : ndarray, شکل (n_source,)
        مقادیر مشاهده‌شده در نقاط منبع (مثلاً سرعت باد)
    variogram_model : str
        نام مدل واریوگرام (`spherical`, `exponential`, `gaussian`, `linear`)
    n_lags : int
        تعداد بازه‌های محاسبه واریوگرام تجربی
    """

    def __init__(
        self,
        coords: NDArray[np.float64],
        values: NDArray[np.float64],
        variogram_model: str = "spherical",
        n_lags: int = 20,
    ) -> None:
        self.coords = np.atleast_2d(np.asarray(coords, dtype=np.float64))
        self.values = np.atleast_1d(np.asarray(values, dtype=np.float64))
        self.n_lags = int(n_lags)
        self.variogram_model = variogram_model

        self._cov_matrix: NDArray[np.float64] | None = None
        self._C_inv: NDArray[np.float64] | None = None
        self._variogram_result: VariogramResult | None = None
        self._fitted: bool = False
        self._nugget: float = 0.0

    # ------------------------------------------------------------------
    def _build_covariance(self, coords_a: NDArray[np.float64], coords_b: NDArray[np.float64]) -> NDArray[np.float64]:
        """محاسبه ماتریس کوواریانس بین دو مجموعه مختصات."""
        from scipy.spatial.distance import cdist
        dist = cdist(np.asarray(coords_a), np.asarray(coords_b))
        return self._covariance_from_dist(dist)

    def _covariance_from_dist(self, dist: NDArray[np.float64]) -> NDArray[np.float64]:
        """تبدیل ماتریس فاصله به ماتریس کوواریانس با استفاده از مدل برازش‌شده."""
        if self._variogram_result is None:
            return np.exp(-dist / max(np.median(dist), 1e-9))

        model_fn = _VARIOGRAM_MODELS[self._variogram_result.model_name]
        sill = self._variogram_result.sill
        nugget = self._variogram_result.nugget
        range_ = self._variogram_result.range_
        gamma = nugget + model_fn(np.maximum(dist, 0.0), sill - nugget, range_)
        cov = sill - gamma
        return np.maximum(cov, 0.0)

    # ------------------------------------------------------------------
    def fit(self) -> None:
        """برازش واریوگرام و محاسبه ماتریس کوواریانس معکوس (یک بار محاسبه می‌شود)."""
        emp = EmpiricalVariogram(self.coords, self.values, n_lags=self.n_lags)
        fitter = VariogramFitter(emp)
        self._variogram_result = fitter.fit(model_name=self.variogram_model)
        self._nugget = self._variogram_result.nugget

        n = self.values.shape[0]
        self._cov_matrix = self._build_covariance(self.coords, self.coords)

        # اضافه کردن ناگت به قطر برای پایداری عددی (در واریوگرام gamma(0)=nugget)
        self._cov_matrix += self._nugget * np.eye(n)

        # اضافه عدد کوچک به قطر اگر ماتریس نزدیک به تکینگ هست
        min_eig = np.linalg.eigvalsh(self._cov_matrix).min()
        if min_eig < 1e-8:
            self._cov_matrix += (1e-6 - min_eig) * np.eye(n)

        self._C_inv = np.linalg.inv(self._cov_matrix)
        self._fitted = True

    # ------------------------------------------------------------------
    def predict(self, target_points: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        تخمین مقدار در نقاط هدف.

        پارامترها
        ----------
        target_points : ndarray, شکل (n_target, 2)
            مختصات نقاط هدف

        خروجی
        -------
        ndarray, شکل (n_target,)
            مقادیر تخمین‌شده
        """
        if not self._fitted or self._C_inv is None:
            self.fit()

        target = np.atleast_2d(np.asarray(target_points, dtype=np.float64))
        n_target = target.shape[0]
        n_source = self.values.shape[0]

        # ماتریس کوواریانس نقاط هدف با نقاط منبع: (n_target, n_source)
        c_T = self._build_covariance(target, self.coords)

        # حل سیستم خطی برای هر نقطه هدف
        results = np.empty(n_target, dtype=np.float64)
        m = self.values.reshape(1, n_source) @ self._C_inv  # (1, n_source)

        for i in range(n_target):
            c_i = c_T[i, :].reshape(1, n_source)  # (1, n_source)
            mu = float((m @ c_i.T)[0, 0])
            results[i] = mu

        return results
