/**
 * نرم‌سازی هندسی مسیر برای نمایش — برش گوشهٔ چایکین (Chaikin corner-cutting).
 *
 * مسیرِ خروجی موتور یک چندخطیِ واقعی با گره‌های گراف است؛ در گوشهٔ چک‌پوینت
 * (جایی که مسیر تغییر جهت میدهد) خطِ خام «گردنِ تیز» می‌سازد و چرخش از یک
 * چک‌پوینت به مقصد بعدی ناگهانی دیده می‌شود. این ابزار فقط برای **نمایش**
 * است: نقطهٔ اول و آخر دقیقاً حفظ می‌شود (سنجاق مبدأ/مقصد جابه‌جا نشود)
 * و گوشه‌های میانی به‌جای شکست ناگهانی، ملایم می‌چرخند.
 */

/** یک نقطهٔ دوبعدی (lon, lat) یا (x, y). */
export type GeomPoint2D = [number, number]

/** یک نقطهٔ سه‌بعدی صحنهٔ دست‌ساز (کیلومتر x/y و z اغراق‌شده). */
export interface GeomPoint3D {
  x: number
  y: number
  z: number
}

/**
 * برش گوشهٔ چایکین روی خط دوبعدی — در هر تکرار، هر ضلع دو نقطه در نسبت
 * ۷۵/۲۵ و ۲۵/۷۵ می‌سازد؛ دو تکرار برای «چرخش نرم» گوشه‌ها کافی است و
 * مایل‌خط‌های مستقیم دست‌نخورده می‌مانند (نقاط میانی روی همان بند می‌افتند).
 */
export function chaikinSmoothLine(points: GeomPoint2D[], iterations = 2): GeomPoint2D[] {
  if (points.length < 3 || iterations < 1) return points.slice()
  let current = points.slice()
  for (let it = 0; it < iterations; it += 1) {
    const next: GeomPoint2D[] = [current[0]]
    for (let i = 0; i < current.length - 1; i += 1) {
      const [ax, ay] = current[i]
      const [bx, by] = current[i + 1]
      next.push([ax * 0.75 + bx * 0.25, ay * 0.75 + by * 0.25])
      next.push([ax * 0.25 + bx * 0.75, ay * 0.25 + by * 0.75])
    }
    next.push(current[current.length - 1])
    current = next
  }
  return current
}

/** برش گوشهٔ چایکین روی خط سه‌بعدی صحنه — x/y/z با هم نرم می‌شوند. */
export function chaikinSmoothXYZ(points: GeomPoint3D[], iterations = 2): GeomPoint3D[] {
  if (points.length < 3 || iterations < 1) return points.slice()
  let current = points.slice()
  for (let it = 0; it < iterations; it += 1) {
    const next: GeomPoint3D[] = [current[0]]
    for (let i = 0; i < current.length - 1; i += 1) {
      const a = current[i]
      const b = current[i + 1]
      next.push({
        x: a.x * 0.75 + b.x * 0.25,
        y: a.y * 0.75 + b.y * 0.25,
        z: a.z * 0.75 + b.z * 0.25,
      })
      next.push({
        x: a.x * 0.25 + b.x * 0.75,
        y: a.y * 0.25 + b.y * 0.75,
        z: a.z * 0.25 + b.z * 0.75,
      })
    }
    next.push(current[current.length - 1])
    current = next
  }
  return current
}
