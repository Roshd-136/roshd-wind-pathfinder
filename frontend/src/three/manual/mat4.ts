/**
 * ماتریس‌های ۴×۴ و بردارهای سه‌بعدی — پیاده‌سازی دستی (بدون کتابخانه).
 *
 * قرارداد ماتریس: ردیف‌محور (row-major)، اعمال ستونیِ بردارهای ستونی —
 * یعنی m41→x وترونهٔ z معکوس (راست‌دست). همه با آرایهٔ تخت Float32Array
 * طول ۱۶ تا بارگذاری در بافر GPU بدون کپی ممکن باشد.
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
  let len = Math.hypot(zx, zy, zz) || 1
  zx /= len; zy /= len; zz /= len
  // x = up × z
  let xx = up[1] * zz - up[2] * zy
  let xy = up[2] * zx - up[0] * zz
  let xz = up[0] * zy - up[1] * zx
  len = Math.hypot(xx, xy, xz)
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
  const out = new Float32Array(16)
  const inv = new Float32Array(16)
  inv[0] = m[5] * m[10] * m[15] - m[5] * m[11] * m[14] - m[9] * m[6] * m[15] + m[9] * m[7] * m[14] + m[13] * m[6] * m[11] - m[13] * m[7] * m[10]
  inv[4] = -m[4] * m[10] * m[15] + m[4] * m[11] * m[14] + m[8] * m[6] * m[15] - m[8] * m[7] * m[14] - m[12] * m[6] * m[11] + m[12] * m[7] * m[10]
  inv[8] = m[4] * m[9] * m[15] - m[4] * m[10] * m[13] - m[8] * m[5] * m[15] + m[8] * m[7] * m[13] + m[12] * m[5] * m[10] - m[12] * m[6] * m[9]
  inv[12] = -m[4] * m[9] * m[14] + m[4] * m[10] * m[13] + m[8] * m[5] * m[14] - m[8] * m[6] * m[13] - m[12] * m[5] * m[10] + m[12] * m[6] * m[9]
  inv[1] = -m[1] * m[10] * m[15] + m[1] * m[11] * m[14] + m[9] * m[2] * m[15] - m[9] * m[3] * m[14] - m[13] * m[2] * m[11] + m[13] * m[3] * m[10]
  inv[5] = m[0] * m[10] * m[15] - m[0] * m[11] * m[14] - m[8] * m[2] * m[15] + m[8] * m[3] * m[14] + m[12] * m[2] * m[11] - m[12] * m[3] * m[10]
  inv[9] = -m[0] * m[9] * m[15] + m[0] * m[10] * m[13] + m[8] * m[1] * m[15] - m[8] * m[2] * m[13] - m[12] * m[1] * m[10] + m[12] * m[2] * m[9]
  inv[13] = m[0] * m[9] * m[14] - m[0] * m[10] * m[13] - m[8] * m[1] * m[14] + m[8] * m[2] * m[14] + m[12] * m[1] * m[10] - m[12] * m[2] * m[9]
  inv[2] = m[1] * m[6] * m[15] - m[1] * m[7] * m[14] - m[5] * m[2] * m[15] + m[5] * m[3] * m[14] + m[13] * m[2] * m[7] - m[13] * m[3] * m[6]
  inv[6] = -m[0] * m[6] * m[15] + m[0] * m[7] * m[14] + m[4] * m[2] * m[15] - m[4] * m[3] * m[14] - m[12] * m[2] * m[7] + m[12] * m[3] * m[6]
  inv[10] = m[0] * m[5] * m[15] - m[0] * m[6] * m[14] - m[4] * m[1] * m[15] + m[4] * m[2] * m[14] + m[12] * m[1] * m[6] - m[12] * m[2] * m[5]
  inv[14] = -m[0] * m[5] * m[14] + m[0] * m[6] * m[13] + m[4] * m[1] * m[14] - m[4] * m[2] * m[13] - m[12] * m[1] * m[6] + m[12] * m[2] * m[5]
  inv[3] = -m[1] * m[6] * m[11] + m[1] * m[7] * m[10] + m[5] * m[2] * m[11] - m[5] * m[3] * m[10] - m[9] * m[2] * m[7] + m[9] * m[3] * m[6]
  inv[7] = m[0] * m[6] * m[11] - m[0] * m[7] * m[10] - m[4] * m[2] * m[11] + m[4] * m[3] * m[10] + m[8] * m[2] * m[7] - m[8] * m[3] * m[6]
  inv[11] = -m[0] * m[5] * m[11] + m[0] * m[6] * m[10] + m[4] * m[1] * m[11] - m[4] * m[2] * m[10] - m[8] * m[1] * m[7] + m[8] * m[2] * m[6]
  inv[15] = m[0] * m[5] * m[10] - m[0] * m[6] * m[9] - m[4] * m[1] * m[10] + m[4] * m[2] * m[9] + m[8] * m[1] * m[6] - m[8] * m[2] * m[5]
  const det = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12]
  if (det === 0) return out
  const k = 1 / det
  for (let i = 0; i < 16; i += 1) out[i] = inv[i] * k
  return out
}
