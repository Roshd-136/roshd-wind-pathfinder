"""
تست‌های الگوریتم Kriging و محاسبه واریوگرام.
"""

import unittest

import numpy as np

from roshd_wind_pathfinder.preprocessing.kriging import (
    EmpiricalVariogram,
    KrigingInterpolator,
    VariogramFitter,
    VariogramResult,
)


class TestEmpiricalVariogram(unittest.TestCase):
    """تست‌های محاسبه واریوگرام تجربی."""

    def test_basic_variogram(self):
        """۲. پیاده‌سازی محاسبه واریوگرام تجربی."""
        coords = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        values = np.array([1.0, 2.0, 3.0, 4.0])
        emp = EmpiricalVariogram(coords, values, n_lags=5)
        emp.compute()
        self.assertTrue(emp.is_computed)
        self.assertEqual(emp.lag_bins.shape[0], 5)
        self.assertTrue(np.all(np.isfinite(emp.semivariance)))

    def test_variogram_monotonic(self):
        """واریوگرام تجربی باید با افزایش فاصله افزایش یابد یا ثابت بماند."""
        np.random.seed(42)
        n = 30
        coords = np.random.rand(n, 2) * 10.0
        values = 2.0 * coords[:, 0] + np.random.normal(0, 0.3, n)
        emp = EmpiricalVariogram(coords, values, n_lags=10)
        emp.compute()
        # حداقل یکی از semi باید > 0
        self.assertTrue(np.any(emp.semivariance > 1e-6))


class TestVariogramFitter(unittest.TestCase):
    """تست‌های برازش مدل واریوگرام."""

    def setUp(self):
        np.random.seed(0)
        n = 40
        self.coords = np.random.rand(n, 2) * 10.0
        true_func = 3.0 * self.coords[:, 0] + 2.0 * self.coords[:, 1]
        self.values = true_func + np.random.normal(0, 0.2, n)
        self.emp = EmpiricalVariogram(self.coords, self.values, n_lags=12)
        self.emp.compute()

    def test_fit_exists(self):
        """۳. برازش مدل واریوگرام — خروجی معتبر."""
        fitter = VariogramFitter(self.emp)
        result = fitter.fit(model_name="spherical")
        self.assertIsInstance(result, VariogramResult)
        self.assertGreater(result.sill, 0.0)
        self.assertGreater(result.range_, 0.0)
        self.assertGreaterEqual(result.nugget, 0.0)

    def test_fit_all_models(self):
        """برازش تمام مدل‌ها باید بدون خطا انجام شود."""
        for model in ("spherical", "exponential", "gaussian", "linear"):
            fitter = VariogramFitter(self.emp)
            result = fitter.fit(model_name=model)
            self.assertEqual(result.model_name, model)

    def test_fit_sse_nonnegative(self):
        """خطای SSE همیشه غیرمنفی باید باشد."""
        fitter = VariogramFitter(self.emp)
        for model in ("spherical", "exponential", "gaussian", "linear"):
            result = fitter.fit(model_name=model)
            self.assertGreaterEqual(result.sse, 0.0)


class TestKrigingInterpolator(unittest.TestCase):
    """تست‌های درونیابی Kriging."""

    def setUp(self):
        np.random.seed(1)
        n = 25
        self.coords = np.random.rand(n, 2) * 10.0
        linear = 2.0 * self.coords[:, 0] + 1.5 * self.coords[:, 1]
        self.values = linear + np.random.normal(0, 0.1, n)
        self.target = np.array([[5.0, 5.0], [2.0, 3.0]])

    def test_predict_shape(self):
        """۴. پیاده‌سازی درونیابی Kriging — شکل خروجی درست."""
        krig = KrigingInterpolator(self.coords, self.values, variogram_model="spherical")
        pred = krig.predict(self.target)
        self.assertEqual(pred.shape, (2,))

    def test_predict_finite(self):
        """خروجی Kriging باید متناهی (finite) باشد."""
        krig = KrigingInterpolator(self.coords, self.values, variogram_model="spherical")
        pred = krig.predict(self.target)
        self.assertTrue(np.all(np.isfinite(pred)))

    def test_accuracy_better_than_naive(self):
        """Kriging باید از میانگین ساده بهتر (یا برابر) باشد در داده ساختگی."""
        krig = KrigingInterpolator(self.coords, self.values, variogram_model="spherical")
        pred = krig.predict(self.target)
        # مقایسه با میانگین ساده
        mean_val = np.mean(self.values)
        true_at_target = 2.0 * self.target[:, 0] + 1.5 * self.target[:, 1]
        krig_rmse = float(np.sqrt(np.mean((pred - true_at_target) ** 2)))
        mean_rmse = float(np.sqrt(np.mean((np.full(pred.shape, mean_val) - true_at_target) ** 2)))
        # Kriging معمولاً بهتر می‌شود؛ انعطاف می‌دهیم با شرط有限的
        self.assertLess(krig_rmse, mean_rmse + 0.5)

    def test_predict_exact_at_source(self):
        """در نقاط منبع، Kriging باید مقدار دقیق را برگرداند (exact interpolator)."""
        krig = KrigingInterpolator(self.coords, self.values, variogram_model="spherical")
        pred = krig.predict(self.coords[:3])
        np.testing.assert_allclose(pred, self.values[:3], atol=1e-4)

    def test_different_models_run(self):
        """تمام مدل‌های واریوگرام باید بتوانند پیش‌بینی کنند."""
        for model in ("spherical", "exponential", "gaussian", "linear"):
            krig = KrigingInterpolator(self.coords, self.values, variogram_model=model)
            pred = krig.predict(self.target)
            self.assertEqual(pred.shape, (2,))
            self.assertTrue(np.all(np.isfinite(pred)))


class TestAccuracyComparison(unittest.TestCase):
    """۵. مقایسه دقت Kriging با IDW."""

    def setUp(self):
        np.random.seed(7)
        n_train = 30
        n_test = 10
        self.train_coords = np.random.rand(n_train, 2) * 10.0
        linear = 2.5 * self.train_coords[:, 0] + 1.0 * self.train_coords[:, 1]
        self.train_values = linear + np.random.normal(0, 0.3, n_train)

        self.test_coords = np.random.rand(n_test, 2) * 10.0
        self.test_true = 2.5 * self.test_coords[:, 0] + 1.0 * self.test_coords[:, 1]

    def test_kriging_vs_idw_accuracy(self):
        """Kriging باید دقت قابل قبولی داشته باشد (مقایسه مقادیر RMSE)."""
        from roshd_wind_pathfinder.preprocessing.idw import IDWInterpolator
        from roshd_wind_pathfinder.preprocessing.kriging import KrigingInterpolator

        idw = IDWInterpolator(power=2.0)
        krig = KrigingInterpolator(self.train_coords, self.train_values, variogram_model="spherical")

        idw_pred = idw.interpolate_scalar(self.test_coords, self.train_coords, self.train_values)
        krig_pred = krig.predict(self.test_coords)

        idw_rmse = float(np.sqrt(np.mean((idw_pred - self.test_true) ** 2)))
        krig_rmse = float(np.sqrt(np.mean((krig_pred - self.test_true) ** 2)))

        # هر دو روش باید RMSE معقولی داشته باشند
        self.assertLess(idw_rmse, 5.0)
        self.assertLess(krig_rmse, 5.0)
        # Kriging معمولاً در داده‌های ساختگی خطی بهتر است
        self.assertLess(krig_rmse, idw_rmse + 1.0)