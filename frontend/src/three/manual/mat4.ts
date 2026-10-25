/**
 * ماتریس‌های ۴×۴ و بردارهای سه‌بعدی — پیاده‌سازی دستی (بدون کتابخانه).
 *
 * قرارداد ماتریس: **ستون‌محور (column-major)** — مثل OpenGL/GLSL. یعنی
 * عناصر ۱۲..۱۴ (انتقال) ستونِ چهارم‌اند و بردارِ محورِ x ماتریسِ view در
 * عناصر ۰..۲ می‌نشیند. ضرب بردارها ستونی است: v′ = M·v با
 * out[col*4+row]. همه با آرایهٔ تخت Float32Array طول ۱۶ تا بارگذاری
 * مستقیم در بافر GPU ممکن باشد. (نسخهٔ قبلیِ سرصفحه به‌اشتباه
 * «ردیف‌محور» می‌گفت — همان سردرگمی که در اولین نوشتنِ invertMat4
 * باگِ دائمیِ پرتوِ برداشت ساخت.)
 */

export type Vec3 = [number, number, number]
export type Mat4 = Float32Array

export function mat4Identity(): Mat4 {
  const m = new Float32Array(16)
  m[0] = 1; m[5] = 1; m[10] = 1; m[15] = 1
  return m
}

/** ضرب a×b (هر دو ستونیِ بردارهای ستونی) — نتیجه در آرایهٔ جدید. */
export function mat4Multiply(a: Mat4, b: Mat4): Mat4 {
  const out = new Float32Array(16)
  for (let col = 0; col < 4; col += 1) {
    for (let row = 0; row < 4; row += 1) {
      let sum = 0
      for (let k = 0; k < 4; k += 1) sum += a[k * 4 + row] * b[col * 4 + k]
      out[col * 4 + row] = sum
    }
  }
  return out
}

/** دوربین دید (view) — نگاه از eye به سمت target؛ up معمولاً (0,0,1). */
export function mat4LookAt(eye: Vec3, target: Vec3, up: Vec3): Mat4 {
  let zx = eye[0] - target[0]
  let zy = eye[1] - target[1]
  let zz = eye[2] - target[2]
  const zLen = Math.hypot(zx, zy, zz)
  if (zLen < 1e-8) {
    // eye == target — محورِ دید بی‌تعریف است؛ به‌جای ماتریسِ صفر/NaN
    // (قبلاً «hypot || 1» بی‌سروصدا مبنا را صفر می‌کرد)، نگاه به بالا
    // فرض می‌شود — خروجیِ قطعی و بدون NaN.
    zx = 0; zy = 0; zz = 1
  } else {
    zx /= zLen; zy /= zLen; zz /= zLen
  }
  // x = up × z
  let xx = up[1] * zz - up[2] * zy
  let xy = up[2] * zx - up[0] * zz
  let xz = up[0] * zy - up[1] * zx
  let len = Math.hypot(xx, xy, xz)
  if (len < 1e-8) {
    // up موازی z — up جایگزین
    const alt: Vec3 = Math.abs(up[2]) > 0.9 ? [1, 0, 0] : [0, 1, 0]
    xx = alt[1] * zz - alt[2] * zy
    xy = alt[2] * zx - alt[0] * zz
    xz = alt[0] * zy - alt[1] * zx
    len = Math.hypot(xx, xy, xz)
  }
  xx /= len; xy /= len; xz /= len
  // y = z × x
  const yx = zy * xz - zz * xy
  const yy = zz * xx - zx * xz
  const yz = zx * xy - zy * xx
  const m = new Float32Array(16)
  m[0] = xx; m[1] = yx; m[2] = zx; m[3] = 0
  m[4] = xy; m[5] = yy; m[6] = zy; m[7] = 0
  m[8] = xz; m[9] = yz; m[10] = zz; m[11] = 0
  m[12] = -(xx * eye[0] + xy * eye[1] + xz * eye[2])
  m[13] = -(yx * eye[0] + yy * eye[1] + yz * eye[2])
  m[14] = -(zx * eye[0] + zy * eye[1] + zz * eye[2])
  m[15] = 1
  return m
}

/** دوربین پرسپکتیو — zNear/zFar تا مرز اعتبار مقیاس صحنه (کیلومتر). */
export function mat4Perspective(fovyRad: number, aspect: number, zNear: number, zFar: number): Mat4 {
  const f = 1 / Math.tan(fovyRad / 2)
  const nf = 1 / (zNear - zFar)
  const m = new Float32Array(16)
  m[0] = f / aspect
  m[5] = f
  m[10] = (zFar + zNear) * nf
  m[11] = -1
  m[14] = 2 * zFar * zNear * nf
  return m
}

/** دوربین عمود (ortho) — نمای بالا برای جابه‌جایی روی صحنه. */
export function mat4Ortho(
  left: number, right: number, bottom: number, top: number, zNear: number, zFar: number,
): Mat4 {
  const m = mat4Identity()
  m[0] = 2 / (right - left)
  m[5] = 2 / (top - bottom)
  m[10] = -2 / (zFar - zNear)
  m[12] = -((right + left) / (right - left))
  m[13] = -((top + bottom) / (top - bottom))
  m[14] = -((zFar + zNear) / (zFar - zNear))
  return m
}

/** چرخش حول محور z (برای چرخش صحنه با کشیدن ماوس). */
export function mat4RotateZ(rad: number): Mat4 {
  const m = mat4Identity()
  const c = Math.cos(rad)
  const s = Math.sin(rad)
  m[0] = c; m[4] = -s
  m[1] = s; m[5] = c
  return m
}

/** چرخش حول محور x — برای زاویهٔ تماشا (نمای مایل تا سرِ بالا). */
export function mat4RotateX(rad: number): Mat4 {
  const m = mat4Identity()
  const c = Math.cos(rad)
  const s = Math.sin(rad)
  m[5] = c; m[9] = -s
  m[6] = s; m[10] = c
  return m
}

/** بزرگ‌نمایی یکنواخت — برای اغراق عمودی زمین. */
export function mat4Scale(x: number, y: number, z: number): Mat4 {
  const m = mat4Identity()
  m[0] = x; m[5] = y; m[10] = z
  return m
}

/** جابه‌جایی — برای بالابردن لایه‌های باد روی ارتفاع. */
export function mat4Translate(x: number, y: number, z: number): Mat4 {
  const m = mat4Identity()
  m[12] = x; m[13] = y; m[14] = z
  return m
}

/** حاصل‌ضرب نهایی MVP — یک بار در هر قاب برای هر مش. */
export function mat4MultiplyVec4(m: Mat4, v: [number, number, number, number]): [number, number, number, number] {
  const x = v[0], y = v[1], z = v[2], w = v[3]
  return [
    m[0] * x + m[4] * y + m[8] * z + m[12] * w,
    m[1] * x + m[5] * y + m[9] * z + m[13] * w,
    m[2] * x + m[6] * y + m[10] * z + m[14] * w,
    m[3] * x + m[7] * y + m[11] * z + m[15] * w,
  ]
}

/** معکوس عمومی ۴×۴ (کوفاکتور) — برای unproject کلیک نقشه. */
export function invertMat4(m: Mat4): Mat4 {
  // وارون با تعریف مستقیمِ ضمیمه: out[col*4+row] = C[row][col]/det که
  // C[row][col] کوفاکتور (± جزءِ کمینهٔ ۳×۳) است. نسخهٔ قبلیِ بسطِ دستی
  // در چند جمله اشتباه داشت و وارونِ کلی را نادرست برمی‌گرداند — که
  // پرتوِ برداشتِ کلیکِ ۳بعدی را کاملاً منحرف می‌کرد («نقطه روی چیزی
  // که کلیک کردم نیست»). با سنجش عددی M·M⁻¹=I و مقایسه با حذف گاوسین
  // راستی‌آزمایی شده.
  const minorDet = (r: number, c: number): number => {
    const rows = [0, 1, 2, 3].filter((x) => x !== r)
    const cols = [0, 1, 2, 3].filter((x) => x !== c)
    const g = (i: number, j: number): number => m[cols[j] * 4 + rows[i]]
    return (
      g(0, 0) * (g(1, 1) * g(2, 2) - g(1, 2) * g(2, 1)) -
      g(0, 1) * (g(1, 0) * g(2, 2) - g(1, 2) * g(2, 0)) +
      g(0, 2) * (g(1, 0) * g(2, 1) - g(1, 1) * g(2, 0))
    )
  }
  const C = new Float32Array(16)
  for (let r = 0; r < 4; r += 1) {
    for (let c = 0; c < 4; c += 1) {
      C[r * 4 + c] = ((r + c) % 2 === 0 ? 1 : -1) * minorDet(r, c)
    }
  }
  const det = m[0] * C[0] + m[4] * C[1] + m[8] * C[2] + m[12] * C[3]
  const out = new Float32Array(16)
  // آستانهٔ نسبی نه تساویِ دقیق: ماتریسِ نزدیک به منفرد (det ~ 1e-15)
  // وارونِ غولآسا و پر از نوفه میداد که بعداً به‌صورت مختصاتِ آشفته
  // ظاهر می‌شد. آستانه‌ی سخنگوی واحد صحنه (کیلومتر) کافی و امن است.
  if (Math.abs(det) < 1e-12) return out
  // وارون = ضمیمه/دترینم؛ ضمیمه در همین نگاشتِ ستون‌محور، هم‌اندیس با
  // کوفاکتورهاست (out[row=r,col=c] = C[r][c]/det) — نه جابه‌جاییِ حافظه‌ای.
  for (let i = 0; i < 16; i += 1) out[i] = C[i] / det
  return out
}
