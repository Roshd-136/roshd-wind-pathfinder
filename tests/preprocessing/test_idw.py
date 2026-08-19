"""
تستهای الگوریتم درونیابی IDW.
"""

import unittest

import numpy as np

from roshd_wind_pathfinder.preprocessing.idw import IDWInterpolator


class TestIDWInterpolator(unittest.TestCase):
    def test_basic_interpolation(self):
        """۱. تست پیاده‌سازی پایه IDW."""
        idw = IDWInterpolator(power=2.0)
        source = np.array([[0.0, 0.0], [1.0, 1.0]])
        values = np.array([10.0, 20.0])
        target = np.array([[0.5, 0.5]])
        result = idw.interpolate_scalar(target, source, values)
        self.assertEqual(result.shape, (1,))
        self.assertGreater(result[0], 0.0)

    def test_power_parameter(self):
        """۲. تنظیم پارامتر توان (power)."""
        idw_low = IDWInterpolator(power=1.0)
        idw_high = IDWInterpolator(power=4.0)
        source = np.array([[0.0, 0.0], [10.0, 10.0]])
        values = np.array([5.0, 15.0])
        target = np.array([[2.0, 2.0]])
        r_low = idw_low.interpolate_scalar(target, source, values)
        r_high = idw_high.interpolate_scalar(target, source, values)
        # توان بالاتر وزن نزدیک‌تر را بیشتر می‌کند
        self.assertNotEqual(r_low, r_high)
        # با توان بالا باید به نقطه نزدیک‌تر (۵.۰) نزدیک‌تر باشد
        self.assertLess(abs(r_high[0] - 5.0), abs(r_low[0] - 5.0))

    def test_accuracy_evaluation(self):
        """۳. ارزیابی دقت در نقاط فاقد داده."""
        idw = IDWInterpolator(power=2.0)
        # داده‌های مصنوعی با الگوی خطی
        source = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
        values = np.array([0.0, 1.0, 2.0])
        # نقطه میانی (۱,۰) باید نزدیک ۱ باشد
        target = np.array([[1.0, 0.0]])
        result = idw.interpolate_scalar(target, source, values)
        self.assertAlmostEqual(result[0], 1.0, delta=0.1)

    def test_speed_optimization_with_max_points(self):
        """۴. بهینه‌سازی سرعت با محدود کردن نقاط."""
        idw_full = IDWInterpolator(power=2.0, max_points=None)
        idw_limited = IDWInterpolator(power=2.0, max_points=2)
        source = np.array([[i, i] for i in range(20)])
        values = np.arange(20, dtype=float)
        target = np.array([[5.0, 5.0]])
        r_full = idw_full.interpolate_scalar(target, source, values)
        r_limited = idw_limited.interpolate_scalar(target, source, values)
        # هر دو باید عدد معقول بدهند
        self.assertTrue(np.isfinite(r_full[0]))
        self.assertTrue(np.isfinite(r_limited[0]))

    def test_blind_spot_comparison(self):
        """۵. مقایسه نتایج در نقاط کور (فاقد داده)."""
        idw = IDWInterpolator(power=2.0)
        # دو نقطه منبع با مقادیر متفاوت
        source = np.array([[0.0, 0.0], [3.0, 3.0]])
        values = np.array([0.0, 30.0])
        # نقطه کور نزدیک به منبع اول
        blind_near = np.array([[0.1, 0.1]])
        # نقطه کور نزدیک به منبع دوم
        blind_far = np.array([[2.9, 2.9]])
        r_near = idw.interpolate_scalar(blind_near, source, values)
        r_far = idw.interpolate_scalar(blind_far, source, values)
        self.assertLess(r_near[0], r_far[0])

    def test_sample_code_execution(self):
        """۶. تهیه نمونه کد تست."""
        idw = IDWInterpolator(power=2.0)
        stations = np.array([[35.7, 51.4], [35.8, 51.5]])
        u_comp = np.array([5.0, 3.0])
        v_comp = np.array([2.0, 1.0])
        grid = np.array([[35.75, 51.45]])
        u_est, v_est = idw.interpolate_wind_field(grid, stations, u_comp, v_comp)
        self.assertEqual(u_est.shape, (1,))
        self.assertEqual(v_est.shape, (1,))
        self.assertTrue(np.isfinite(u_est[0]))
        self.assertTrue(np.isfinite(v_est[0]))

    def test_vectorization_performance(self):
        """۷. بهینه‌سازی سرعت محاسبات (بردارسازی)."""
        idw = IDWInterpolator(power=2.0)
        source = np.random.rand(50, 2) * 10
        values = np.random.rand(50)
        target = np.random.rand(100, 2) * 10
        u_est = idw.interpolate_scalar(target, source, values)
        self.assertEqual(u_est.shape, (100,))
        self.assertTrue(np.all(np.isfinite(u_est)))


if __name__ == "__main__":
    unittest.main()
