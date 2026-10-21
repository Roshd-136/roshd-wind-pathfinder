/**
 * رندرر WebGL خام صحنهٔ سه‌بعدی — بدون هیچ کتابخانهٔ سه‌بعدی (خواستهٔ کاربر:
 * «کل صحنهٔ ۳بعدی را دستی بکش، از کتابخانهٔ آماده استفاده نکن»).
 *
 * استراتژی عملکرد (سریع‌ترین ناوبری + پیکان‌های باد همیشه نمایان):
 *  ۱) **برش کاشی‌وار زمین** — زمین در کاشی‌های شاخص‌دار تقسیم شده؛ هر قاب فقط
 *     کاشی‌های داخل مخروط دید draw می‌شوند — «فقط بخشی که دوربین روی آن است».
 *  ۲) یک‌بار بارگذاری بافر در GPU؛ هر قاب فقط ماتریس‌ها عوض می‌شود.
 *  ۳) دوربین مداری سبک (yaw/pitch/zoom) بدون فیزیک سنگین.
 */

import { invertMat4, mat4LookAt, mat4Multiply, mat4Perspective, type Mat4, type Vec3 } from './mat4'
import {
  ROUTE_TUBE_RADIUS_KM,
  SPLINE_SAMPLES,
  VERTICAL_EXAGGERATION,
  MARKER_DOT_RADIUS_KM,
  buildMarkerDot,
  buildRouteTube,
  buildTerrainTiles,
  buildWindArrows,
  isInTerrainFrame,
  kmToLonLat,
  lonLatToKm,
  makeFrame,
  parseTerrainCsv,
  smoothRoute,
  terrainElevationAt,
  type Bounds6,
  type SceneFrame,
  type TerrainData,
} from './scene'
import type { Coordinate, Coordinate3D, WindField } from '../../types/routing'
import { chaikinSmoothXYZ } from '../../utils/geometry'
import { cumulativeFractions, fightAtFraction, fightColor01 } from '../../utils/windFight'
// سقفِ ارتفاعِ پرواز — همان مرزِ بالاترین باندِ لایهٔ باد؛ موتور مسیر در
// قفل‌های بالاتر از این «مسیر عبوری ندارد» (زمین ناهوار) رد می‌کند، پس
// کشیدنِ محور ارتفاع را همین‌جا به قلمروِ معتبر محدود می‌کنیم.
import { WIND_ALTITUDE_MAX } from '../../config/routing'

/** حاشیهٔ پذیرش برخوردِ واقعی با سطح زمین (ک.م) — کلیک روی خودِ نوار. */
const MARCH_PICK_PAD_KM = 8
/** کفِ حاشیهٔ پذیرش «صفحهٔ تخت» (ک.م) — واقعیِ پذیرش با مقیاسِ دوربین
 * (camDist×۱٫۱) بزرگ می‌شود تا دشتِ اطرافِ زمینِ دیده‌شده در هر زوم
 * قابل گذاشتنِ چک‌پوینت باشد؛ فراتر از آن، افقِ واقعا دور صادقانه
 * «بیرون از کادر داده» می‌گوید. */
const PLANE_PICK_PAD_KM = 150

// ————— شیدرها — GLSL ES 1.00 —————

const VS_MAIN = `
attribute vec3 aPos;
attribute vec3 aColor;
uniform mat4 uMVP;
varying vec3 vColor;
void main() {
  gl_Position = uMVP * vec4(aPos, 1.0);
  vColor = aColor;
}
`

const FS_MAIN = `
precision mediump float;
varying vec3 vColor;
uniform float uOpacity;
void main() {
  gl_FragColor = vec4(vColor, uOpacity);
}
`

// ————— ابزار GL —————

type Gl = WebGLRenderingContext

function compileShader(gl: Gl, type: number, src: string): WebGLShader {
  const sh = gl.createShader(type)
  if (!sh) throw new Error('createShader failed')
  gl.shaderSource(sh, src)
  gl.compileShader(sh)
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(sh) ?? ''
    throw new Error(`shader compile failed: ${log}`)
  }
  return sh
}

function linkProgram(gl: Gl, vsSrc: string, fsSrc: string): WebGLProgram {
  const p = gl.createProgram()
  if (!p) throw new Error('createProgram failed')
  const vs = compileShader(gl, gl.VERTEX_SHADER, vsSrc)
  const fs = compileShader(gl, gl.FRAGMENT_SHADER, fsSrc)
  gl.attachShader(p, vs)
  gl.attachShader(p, fs)
  gl.linkProgram(p)
  gl.deleteShader(vs)
  gl.deleteShader(fs)
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
    throw new Error(`program link failed: ${gl.getProgramInfoLog(p) ?? ''}`)
  }
  return p
}

/** AABB شش‌تایی: [minX,minY,minZ,maxX,maxY,maxZ]. */
export type Bounds = Bounds6

interface GpuMesh {
  vbo: WebGLBuffer
  ibo: WebGLBuffer
  indexCount: number
  bytesPerIndex: number
  mode: number
}

/** مش گیمبال با محور مرتبط — برای کم‌نوری محورهای غیرهاور. */
interface GizmoMesh {
  mesh: GpuMesh
  axis: GizmoAxis
}

/** آپلود مش مثلثی بدون شاخص — یک مثلث هر ۳ رأس، از interleaved [x,y,z,r,g,b]. */
function uploadTriangles(gl: Gl, positions: Float32Array, colors: Float32Array): GpuMesh {
  const vbo = gl.createBuffer()
  if (!vbo) throw new Error('createBuffer failed')
  const vertexCount = positions.length / 3
  const interleaved = new Float32Array(vertexCount * 6)
  for (let v = 0; v < vertexCount; v += 1) {
    interleaved[v * 6] = positions[v * 3]
    interleaved[v * 6 + 1] = positions[v * 3 + 1]
    interleaved[v * 6 + 2] = positions[v * 3 + 2]
    interleaved[v * 6 + 3] = colors[v * 3]
    interleaved[v * 6 + 4] = colors[v * 3 + 1]
    interleaved[v * 6 + 5] = colors[v * 3 + 2]
  }
  gl.bindBuffer(gl.ARRAY_BUFFER, vbo)
  gl.bufferData(gl.ARRAY_BUFFER, interleaved, gl.STATIC_DRAW)
  return { vbo, ibo: null as unknown as WebGLBuffer, indexCount: vertexCount, bytesPerIndex: 2, mode: gl.TRIANGLES }
}

/** آپلود مش شاخص‌دار — بافر interleaved [x,y,z,r,g,b] (۱۲+۱۲ بایت). */
function uploadIndexed(
  gl: Gl,
  positions: Float32Array,
  colors: Float32Array,
  indices: Uint32Array,
  mode: number,
): GpuMesh {
  const vbo = gl.createBuffer()
  const ibo = gl.createBuffer()
  if (!vbo || !ibo) throw new Error('createBuffer failed')
  const vertexCount = positions.length / 3
  const interleaved = new Float32Array(vertexCount * 6)
  for (let v = 0; v < vertexCount; v += 1) {
    interleaved[v * 6] = positions[v * 3]
    interleaved[v * 6 + 1] = positions[v * 3 + 1]
    interleaved[v * 6 + 2] = positions[v * 3 + 2]
    interleaved[v * 6 + 3] = colors[v * 3]
    interleaved[v * 6 + 4] = colors[v * 3 + 1]
    interleaved[v * 6 + 5] = colors[v * 3 + 2]
  }
  gl.bindBuffer(gl.ARRAY_BUFFER, vbo)
  gl.bufferData(gl.ARRAY_BUFFER, interleaved, gl.STATIC_DRAW)
  let maxIndex = 0
  for (let i = 0; i < indices.length; i += 1) {
    if (indices[i] > maxIndex) maxIndex = indices[i]
  }
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo)
  let bytesPerIndex: number
  if (maxIndex > 65535) {
    const ext = gl.getExtension('OES_element_index_uint')
    if (!ext) throw new Error('OES_element_index_uint در دسترس نیست')
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW)
    bytesPerIndex = 4
  } else {
    const u16 = new Uint16Array(indices.length)
    u16.set(indices)
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, u16, gl.STATIC_DRAW)
    bytesPerIndex = 2
  }
  return { vbo, ibo, indexCount: indices.length, bytesPerIndex, mode }
}

// ————— برش مخروط دید — هشت گوشهٔ AABB در فضای کلیپ —————

function aabbVisible(mvp: Mat4, b: Bounds, margin = 1.25): boolean {
  let anyFront = false
  let anyInside = false
  for (let ci = 0; ci < 8; ci += 1) {
    const x = ci & 1 ? b[3] : b[0]
    const y = ci & 2 ? b[4] : b[1]
    const z = ci & 4 ? b[5] : b[2]
    const cw = mvp[3] * x + mvp[7] * y + mvp[11] * z + mvp[15]
    if (cw <= 0) continue
    anyFront = true
    const w = cw * margin
    const cx = mvp[0] * x + mvp[4] * y + mvp[8] * z + mvp[12]
    const cy = mvp[1] * x + mvp[5] * y + mvp[9] * z + mvp[13]
    const cz = mvp[2] * x + mvp[6] * y + mvp[10] * z + mvp[14]
    if (cx >= -w && cx <= w && cy >= -w && cy <= w && cz >= -w && cz <= w) {
      anyInside = true
      break
    }
  }
  return anyFront && anyInside
}

// ————— گیمبال ویرایش نقطه — هندسه —————

/** اندازهٔ فلش‌ها بر حسب کیلومتر صحنه — با فاصلهٔ دوربین مقیاس می‌گیرد. */
const GIZMO_ARROW_KM = 14

/**
 * یک فلش سه‌بعدی از مبدأ در جهت dir — بدنهٔ منشوری با مقطع لوزی + سر هرمی.
 * فلشِ تخت (دو مثلث) از نمای سَرخِمو به «خط» فرومی‌ریزد و در نمای افقی
 * محورهای افقی کلاً ناپدید می‌شدند؛ حجمِ سه‌بعدی از هر زاویه دیده می‌شود.
 * قاعدهٔ بدنه دقیقاً روی نقطهٔ انتخاب‌شده است (بدون فاصلهٔ اولیه).
 */
function buildGizmoArrow(origin: Vec3, dir: Vec3, rgb: [number, number, number], lenKm: number): { positions: Float32Array; colors: Float32Array } {
  const [dx, dy, dz] = dir
  // دو بردار عمود بر محور — dir همیشه یک محور اصلی است؛ دو محور دیگر کافی‌اند
  const p1: Vec3 = Math.abs(dz) > 0.9 ? [1, 0, 0] : [-dy, dx, 0]
  const p2: Vec3 = Math.abs(dz) > 0.9 ? [0, 1, 0] : [0, 0, 1]
  const w = lenKm * 0.05      // نصف ضخامت بدنه (نیم‌لوزی)
  const headW = lenKm * 0.14  // نیم‌پهنای قاعدهٔ سرِ هرمی
  const bodyLen = lenKm * 0.6
  const at = (t: number): Vec3 => [origin[0] + dx * t, origin[1] + dy * t, origin[2] + dz * t]
  // چهار گوشهٔ مقطع لوزی: +p1 و +p2 و −p1 و −p2
  const ringCorner = (c: Vec3, hw: number, i: number): Vec3 => {
    const v = i % 2 === 0 ? p1 : p2
    const s = i < 2 ? hw : -hw
    return [c[0] + v[0] * s, c[1] + v[1] * s, c[2] + v[2] * s]
  }
  const tip = at(lenKm)
  const pos: number[] = []
  const col: number[] = []
  const push = (v: Vec3, s: number): void => {
    pos.push(v[0], v[1], v[2])
    col.push(Math.min(rgb[0] * s, 1), Math.min(rgb[1] * s, 1), Math.min(rgb[2] * s, 1))
  }
  // روشنایی هر وجه — خوانایی حجمی از هر زاویه
  const shades = [0.95, 0.75, 0.68, 0.82]
  for (let i = 0; i < 4; i += 1) {
    const j = (i + 1) % 4
    const a0 = ringCorner(origin, w, i)
    const a1 = ringCorner(origin, w, j)
    const b0 = ringCorner(at(bodyLen), headW, i)
    const b1 = ringCorner(at(bodyLen), headW, j)
    const sh = shades[i] ?? 0.8
    // بدنه — وجه لوزی از نقطه تا انتهای بدنه (دو مثلث)
    push(a0, sh)
    push(b0, sh)
    push(b1, sh)
    push(a0, sh)
    push(b1, sh)
    push(a1, sh)
    // سر — قاعده تا نوک
    push(b0, 1.15)
    push(b1, 1.15)
    push(tip, 1.3)
  }
  return { positions: new Float32Array(pos), colors: new Float32Array(col) }
}

// ————— صحنه —————

interface TerrainTileRange {
  start: number
  count: number
  bounds: Bounds
}

export interface Manual3DSceneOptions {
  path3d: Coordinate3D[] | null
  windFields: WindField[]
  origin?: Coordinate | null
  destination?: Coordinate | null
  /** چک‌پوینت‌ها — ممکن است alt (ارتفاع MSL متر) داشته باشند. */
  checkpoints?: Array<Coordinate & { alt?: number }>
  /** درصد مقابله با باد برای هر نقطهٔ مسیر (هم‌طولِ path3d) — رنگِ لوله؛
   * null/ناموجود = رنگِ ثابت سفیدِ قبلی. */
  fightProfile?: number[] | null
}

// ————— ویرایشگر نقطه (گیمبال سه‌محوره) —————
// محورها با نام انسانی: «شرق–غرب»، «شمال–جنوب»، «ارتفاع». کشیدن هر فلش،
// مختصات همان نقطه را روی همان محور جابه‌جا می‌کند؛ نتیجه در pointerup با
// onPointEdit به صفحه گزارش می‌شود (نه در هر حرکت — تا استور طوفانی نشود).

export type EditTargetKind = 'origin' | 'destination' | 'checkpoint'

export interface EditTarget {
  kind: EditTargetKind
  /** مبدأ/مقصد: ‎-۱؛ چک‌پوینت: اندیس در آرایه checkpoints */
  index: number
  /** ارتفاع گزارش‌شده پس از کشیدن محور «ارتفاع» (متر MSL) — وگرنه نامشخص. */
  altM?: number
}

export type GizmoAxis = 'ew' | 'ns' | 'up'

/** دلیل نل‌شدن برداشت کلیک — برای پیامِ روشن به کاربر. */
export type PickMissKind = 'outside' | 'sky'

interface AxisSpec {
  axis: GizmoAxis
  dir: Vec3
  rgb: [number, number, number]
}

const GIZMO_AXES: AxisSpec[] = [
  { axis: 'ew', dir: [1, 0, 0], rgb: [0.94, 0.27, 0.27] },   // شرق–غرب — قرمز
  { axis: 'ns', dir: [0, 1, 0], rgb: [0.13, 0.77, 0.37] },   // شمال–جنوب — سبز
  { axis: 'up', dir: [0, 0, 1], rgb: [0.22, 0.74, 0.96] },   // ارتفاع — آبی
]

const TERRAIN_TILE_GRID = 6
const FOV_RAD = 0.9

export class Manual3DScene {
  /** دوربین مداری — yaw/pitch/فاصله/هدف. */
  camYaw = -Math.PI / 4
  camPitch = 0.95
  camDist = 150
  camTarget: Vec3 = [0, 0, 0.8]

  private gl: Gl
  private canvas: HTMLCanvasElement
  /** حالت درگ: پن (کلید میانی/Shift) یا چرخش مداری. */
  private panMode = false
  private frame: SceneFrame | null = null
  private terrainData: TerrainData | null = null
  private program: WebGLProgram | null = null
  private uMVP: WebGLUniformLocation | null = null
  private uOpacity: WebGLUniformLocation | null = null
  private aPos = -1
  private aColor = -1
  private terrain: GpuMesh | null = null
  private terrainTiles: TerrainTileRange[] = []
  private arrowMeshes: GpuMesh[] = []
  /** محدودهٔ مجاز برداشت کلیک زمین (km) — زمین ∪ مسیر ∪ نشانگرها + ۸ km */
  private pickBoundsKm: { minX: number; minY: number; maxX: number; maxY: number } | null = null
  private markerMeshes: GpuMesh[] = []
  private routeMesh: GpuMesh | null = null
  private rafId = 0
  private disposed = false
  // تعامل
  private pointerDown = false
  private lastX = 0
  private lastY = 0
  private dragMoved = false
  /** کاربر دوربین را جابه‌جا کرده؟ — تا تعویض حالت، نما را به‌هم نزنیم. */
  private userMoved = false
  /** اثر مسیر قبلی — تشخیص «مسیر عوض شد» برای کادر کردن دوبارهٔ نما. */
  private lastRouteKey = ''
  /** کلیک بدون کشیدن — به صفحهٔ بالادست (مبدأ/مقصد/اطلاعات نقطه). */
  onMapClick: ((lat: number, lon: number) => void) | null = null
  /** کلیک برداشتنیِ «افزودن چک‌پوینت» که مختصات نداد — برای بازخوردِ بی‌سکوت.
   *  kind: 'outside' = بیرون کادر داده، 'sky' = پرتو به آسمان. */
  onPickMiss: ((kind: PickMissKind) => void) | null = null
  /** دلیل آخرین ردِ برداشت — گزارش به صفحه در حالت «افزودن چک‌پوینت». */
  private lastPickMiss: PickMissKind | null = null

  // ————— ویرایشگر نقطه (گیمبال) —————
  /** هدف فعال ویرایش؛ null = گیمبال پنهان. */
  private editTarget: EditTarget | null = null
  /** موقعیت صحنه‌ای هدف — کشیده‌شده زنده، سپس در drop گزارش می‌شود. */
  private editPosKm: Vec3 | null = null
  /** آخرین گزارش drop — برای شناختن «اکوی» همان جابه‌جایی در setEditTarget. */
  private lastEditReport: { target: EditTarget; lat: number; lon: number } | null = null
  /** ارتفاعِ سفارشیِ هدفِ ویرایش (از آخرین setEditTarget) — درگِ افقی نباید
   * سطحِ پروازی که کاربر با محورِ «ارتفاع» گذاشته بود را پاک کند؛ قبلاً
   * میرفت و گوی بی‌بهانه به زمین می‌چسبید. */
  private editPriorAltM: number | undefined = undefined
  /** محور در حال کشیدن. */
  private dragAxis: GizmoAxis | null = null
  /** فاصلهٔ دوربین هنگام آخرین بازسازیِ گیمبال — برای گاززدنِ بازسازیِ wheel. */
  private lastGizmoDist = 0
  /** پیکان زیر نشانگر — برای هایلایت هاور. */
  private hoverAxis: GizmoAxis | null = null
  /** مش‌های گیمبال — هر تغییر بازسازی می‌شوند (سبک‌اند). */
  private gizmoMeshes: GizmoMesh[] = []
  /** وضعیت موقعیت هدف هنگام شروع کشیدن — جابه‌جایی نسبی صفحه → صحنه. */
  private dragStartScreen: { x: number; y: number } | null = null
  private dragStartPosKm: Vec3 | null = null
  /** گزارش جابه‌جایی نقطه — lat/lon نهایی پس از رها کردن فلش. */
  onPointEdit: ((target: EditTarget, coord: { lat: number; lon: number }) => void) | null = null

  // ————— انتخاب نقطه با کلیک (روی گوی نشانگر) —————
  /** مکان صحنه‌ای هر گوی نشانگر — برای hit-test کلیک. */
  private markerDots: Array<{ target: EditTarget; posKm: Vec3 }> = []
  /** شعاع رسم گوی (ک.م) — با فاصلهٔ دوربین مقیاس می‌گیرد تا در نمای دور هم
   * گویِ «روی چه کلیک کرده» خوانا بماند (شعاع ثابت ۰٫۹ ک.م در دوربینِ دبین
   * ~۴ پیکسل می‌شد و نامرئیِ مؤثر بود). */
  private markerDotRadiusKm = MARKER_DOT_RADIUS_KM
  /** کلیک روی گوی نشانگر — صفحه باید گیمبال را روی همان نقطه بنشاند. */
  onPointPick: ((target: EditTarget | null) => void) | null = null

  /** موقعیتِ صفحه‌ایِ گوی‌های نشانگر در پایان هر فریم — لایهٔ DOMِ برچسبِ
   * اعدادِ چک‌پوینت را همگام می‌کند (بدون رندرِ مجددِ React؛ همگام‌سازیِ
   * دستورالعملی). `behind` یعنی پشتِ دوربین است و برچسب باید پنهان شود. */
  onMarkerScreens:
    | ((dots: Array<{ target: EditTarget; x: number; y: number; behind: boolean; rPx: number }>) => void)
    | null = null

  /**
   * حالت «افزودن چک‌پوینت» — رابط کاربری روشنش می‌کند و کلیک بعدیِ خالیِ
   * دشت از `onMapClick` به‌عنوان نقطهٔ چک‌پوینت ثبت می‌شود. در این حالت
   * نشانگر موس همیشه crosshair است؛ هاورِ grab/pointer گیمبال و گوی‌ها
   * جای وضعیت «کلیک = ثبت» را نمی‌گیرد.
   */
  placingPoint = false

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas
    const gl = (canvas.getContext('webgl', { antialias: true, depth: true }) ||
      canvas.getContext('experimental-webgl')) as Gl | null
    if (!gl) throw new Error('WebGL در دسترس نیست')
    this.gl = gl
    this.attachEvents()
  }

  /** CSV ارتفاع را می‌گیرد و زمین را آماده می‌کند — یک‌بار در mount. */
  async initTerrain(): Promise<void> {
    const resp = await fetch('/data/khorasan_terrain.csv')
    if (!resp.ok) throw new Error('CSV ارتفاع دریافت نشد')
    this.terrainData = parseTerrainCsv(await resp.text())
    const t = this.terrainData
    const bbox: [number, number, number, number] = [
      t.lons[0],
      t.lats[0],
      t.lons[t.lons.length - 1],
      t.lats[t.lats.length - 1],
    ]
    this.frame = makeFrame(bbox)
    const tiles = buildTerrainTiles(this.terrainData, this.frame, 72, TERRAIN_TILE_GRID)
    // زمین یک مش کل + بازهٔ شاخص per کاشی (برش بخش دیده‌شده)
    const gl = this.gl
    const vbo = gl.createBuffer()
    const ibo = gl.createBuffer()
    if (!vbo || !ibo) throw new Error('createBuffer failed')
    const vertexCount = tiles.positions.length / 3
    const interleaved = new Float32Array(vertexCount * 6)
    for (let v = 0; v < vertexCount; v += 1) {
      interleaved[v * 6] = tiles.positions[v * 3]
      interleaved[v * 6 + 1] = tiles.positions[v * 3 + 1]
      interleaved[v * 6 + 2] = tiles.positions[v * 3 + 2]
      interleaved[v * 6 + 3] = tiles.colors[v * 3]
      interleaved[v * 6 + 4] = tiles.colors[v * 3 + 1]
      interleaved[v * 6 + 5] = tiles.colors[v * 3 + 2]
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo)
    gl.bufferData(gl.ARRAY_BUFFER, interleaved, gl.STATIC_DRAW)
    const maxIndex = tiles.indices.reduce((m, v) => Math.max(m, v), 0)
    let bytesPerIndex = 2
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo)
    if (maxIndex > 65535) {
      if (!gl.getExtension('OES_element_index_uint')) throw new Error('OES_element_index_uint لازم است')
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, tiles.indices, gl.STATIC_DRAW)
      bytesPerIndex = 4
    } else {
      const u16 = new Uint16Array(tiles.indices.length)
      u16.set(tiles.indices)
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, u16, gl.STATIC_DRAW)
    }
    this.terrain = { vbo, ibo, indexCount: tiles.indices.length, bytesPerIndex, mode: gl.TRIANGLES }
    this.terrainTiles = tiles.tiles.map((tile) => ({
      start: tile.start,
      count: tile.end - tile.start,
      bounds: tile.bounds,
    }))
  }

  /** بازسازی مش‌های پویا (پیکان‌های باد + مسیر) — با هر تغییر داده. */
  rebuildDynamic(options: Manual3DSceneOptions): void {
    if (!this.frame || !this.terrainData) return
    const gl = this.gl
    const frame = this.frame
    for (const m of this.arrowMeshes) {
      gl.deleteBuffer(m.vbo)
      gl.deleteBuffer(m.ibo)
    }
    this.arrowMeshes = []
    if (this.routeMesh) {
      gl.deleteBuffer(this.routeMesh.vbo)
      gl.deleteBuffer(this.routeMesh.ibo)
      this.routeMesh = null
    }
    // پیکان‌های باد هر لایه در ارتفاع خودش — مثلث‌های توپُر (نوار بدنه + سر)؛
    // بدون شاخص — یک مثلث هر ۳ رأس (GL_LINES با پهنای ۱px در نمای کلی دیده نمی‌شد)
    this.arrowMeshes = options.windFields.map((f, i) => {
      const arrows = buildWindArrows(f, frame, this.terrainData as TerrainData, i)
      return uploadTriangles(gl, arrows.positions, arrows.colors)
    })
    // لولهٔ مسیر از path_3d واقعی (ارتفاع متر MSL → کیلومتر اغراق‌شده) +
    // ستون‌های نشانگر مبدأ/مقصد/چک‌پوینت (پین‌های عمودی صحنهٔ مسیریابی)
    if (options.path3d && options.path3d.length > 1) {
      const pts = options.path3d.map((p) => {
        const [x, y] = lonLatToKm(frame, p.lon, p.lat)
        // لوله نباید زیر زمین برود — حداقل همان فاصلهٔ امن پیکان‌ها از زمین
        const groundM = terrainElevationAt(this.terrainData as TerrainData, p.lat, p.lon)
        const altM = Math.max(p.alt, groundM + 200)
        return { x, y, z: (altM / 1000) * VERTICAL_EXAGGERATION }
      })
      // برش گوشهٔ چایکین پیش از اسپلاین — در چک‌پوینت‌ها به‌جای گردنِ تیزِ
      // تغییر جهت، چرخش ملایم دیده شود؛ سر و ته مسیر دقیق می‌ماند تا
      // سنجاق‌های مبدأ/مقصد سر جایشان بمانند.
      const rounded = chaikinSmoothXYZ(pts, 2)
      const spline = smoothRoute(rounded, SPLINE_SAMPLES)
      // رنگ‌آمیزیِ مقابله با باد — هر حلقهٔ لوله از کسرِ فاصله‌اش در مسیر،
      // درصدِ مقابله را از پروفایلِ نقاطِ اصلی می‌گیرد (سفید ۰٪ تا سرخ ۱۰۰٪).
      // ناهم‌طولیِ پروفایل با مسیر (نتیجهٔ کهنه) بدونِ رنگ است تا مسیرِ غلط
      // رنگی نشود.
      const profileLen = options.path3d.length
      const profile =
        options.fightProfile && options.fightProfile.length === profileLen
          ? options.fightProfile
          : null
      const pathFracs = profile ? cumulativeFractions(options.path3d) : null
      const tube =
        profile && pathFracs
          ? buildRouteTube(spline, ROUTE_TUBE_RADIUS_KM, undefined, undefined, (f) =>
              fightColor01(fightAtFraction(profile, pathFracs, f)),
            )
          : buildRouteTube(spline, ROUTE_TUBE_RADIUS_KM)
      this.routeMesh = uploadIndexed(gl, tube.positions, tube.colors, tube.indices, gl.TRIANGLES)

      // مرکزِ نما = مسیر، نه مبدأ: اگر کاربر دوربین را نسوده — یا مسیر عوض
      // شده — کادر دوربین روی وسط کادرِ مسیر می‌نشیند.
      const routeKey = options.path3d.map((p) => p.lon.toFixed(4)).join(',') + '|' + options.path3d.map((p) => p.lat.toFixed(4)).join(',')
      const routeChanged = routeKey !== this.lastRouteKey
      this.lastRouteKey = routeKey
      if (!this.userMoved || routeChanged) {
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
        for (const p of pts) {
          if (p.x < minX) minX = p.x
          if (p.y < minY) minY = p.y
          if (p.x > maxX) maxX = p.x
          if (p.y > maxY) maxY = p.y
        }
        const cx = (minX + maxX) / 2
        const cy = (minY + maxY) / 2
        const spanKm = Math.max(maxX - minX, maxY - minY, 8)
        // کمی فاصلهٔ اضافه تا مسیر کامل با حاشیه در کادر بنشیند
        const dist = Math.min(Math.max(spanKm * 1.15, 25), 600)
        // دوربینِ دست‌کاری‌شده فقط با اجبارِ واقعی تکان می‌خورد: مرکزِ مسیر
        // تازه خیلی بیرونِ دید رفته یا مسیر خیلی بزرگ‌تر از دید است.
        // قبلاً هر recalc دوربین را یکجا yank می‌کرد و حسِ گسست می‌داد؛
        // recalcِ کوچک (CP نزدیک) صحنه را سرِ جایش نگه می‌دارد.
        const halfView = Math.tan(FOV_RAD / 2) * this.camDist * 1.5
        const farFromView =
          Math.hypot(cx - this.camTarget[0], cy - this.camTarget[1]) > halfView ||
          spanKm > halfView * 2.4
        if (!this.userMoved || (routeChanged && farFromView)) {
          this.camTarget = [cx, cy, this.camTarget[2]]
          this.camDist = dist
        }
      }
    }
    // گوی‌های نشانگر — مبدأ/مقصد/چک‌پوینت مثل «نقطه» (نه ستون/خط)
    for (const m of this.markerMeshes) {
      gl.deleteBuffer(m.vbo)
      gl.deleteBuffer(m.ibo)
    }
    this.markerMeshes = []
    this.markerDots = []
    // شعاع گوی متناسب با فاصلهٔ دوربین (≈ ۱٪ پوشش دید) — کف ۰٫۹ ک.م برای نزدیک
    this.markerDotRadiusKm = Math.max(MARKER_DOT_RADIUS_KM, this.camDist * 0.018)
    const markers: Array<{ lat: number; lon: number; color: string; alt?: number; target: EditTarget }> = []
    if (options.origin) markers.push({ ...options.origin, color: '#22c55e', target: { kind: 'origin', index: -1 } })
    if (options.destination) markers.push({ ...options.destination, color: '#ef4444', target: { kind: 'destination', index: -1 } })
    ;(options.checkpoints ?? []).forEach((cp, i) => markers.push({ ...cp, color: '#f59e0b', target: { kind: 'checkpoint', index: i } }))
    for (const mk of markers) {
      const dot = buildMarkerDot(frame, this.terrainData as TerrainData, mk.lat, mk.lon, mk.color, this.markerDotRadiusKm, mk.alt)
      this.markerMeshes.push(uploadIndexed(gl, dot.positions, dot.colors, dot.indices, gl.TRIANGLES))
      const [x, y] = lonLatToKm(frame, mk.lon, mk.lat)
      const groundM = terrainElevationAt(this.terrainData as TerrainData, mk.lat, mk.lon)
      // ارتفاع گوی: ذخیره‌شده (کشیدن محور «ارتفاع») یا سطح زمین؛ بیرونِ
      // کادرِ زمین سطحِ دیدِ کاربر همان صفحهٔ تراز است (نه ارتفاعِ چسبیدهٔ
      // لبهٔ کادر) تا گوی دقیقاً زیرِ محلِ کلیک دیده شود.
      const altM = mk.alt ?? (isInTerrainFrame(this.terrainData as TerrainData, mk.lat, mk.lon) ? groundM : 0)
      this.markerDots.push({
        target: mk.target,
        posKm: [x, y, (altM / 1000) * VERTICAL_EXAGGERATION],
      })
    }
    // محدودهٔ برداشت کلیک (پیکان‌گیری زمین) — کادر زمین ∪ مسیر ∪ نشانگرها،
    // با حاشیهٔ ۸ کیلومتر. قبلاً فقط پوشش CSV زمین قبول می‌شد؛ مسیر و
    // چک‌پوینت‌ها می‌توانستند تا جنوبِ آن کادر امتداد داشته باشند و کلیکِ
    // کاربر روی همان دشتِ دیدنی (بیرون کادر ولی نزدیک مسیر) بی‌صدا null
    // می‌شد — «نمی‌توانم چک‌پوینت در ۳بعدی اضافه کنم». حالا هر نقطهٔ نزدیک
    // مسیر/نشانگرها هم پذیرفته می‌شود و نقاط دور و بی‌ربط مردود می‌مانند.
    let minX = 0
    let minY = 0
    let maxX = frame.widthKm
    let maxY = frame.heightKm
    const widen = (x: number, y: number): void => {
      if (x < minX) minX = x
      if (y < minY) minY = y
      if (x > maxX) maxX = x
      if (y > maxY) maxY = y
    }
    for (const m of this.markerDots) widen(m.posKm[0], m.posKm[1])
    if (options.path3d && options.path3d.length > 1) {
      for (const p of options.path3d) widen(...(lonLatToKm(frame, p.lon, p.lat) as [number, number]))
    }
    const pad = 8
    this.pickBoundsKm = { minX: minX - pad, minY: minY - pad, maxX: maxX + pad, maxY: maxY + pad }
  }

  dispose(): void {
    this.disposed = true
    cancelAnimationFrame(this.rafId)
    this.canvas.removeEventListener('pointerdown', this.onPointerDown)
    window.removeEventListener('pointermove', this.onPointerMove)
    window.removeEventListener('pointerup', this.onPointerUp)
    this.canvas.removeEventListener('wheel', this.onWheel)
    const gl = this.gl
    if (this.terrain) {
      gl.deleteBuffer(this.terrain.vbo)
      gl.deleteBuffer(this.terrain.ibo)
      this.terrain = null
    }
    for (const m of this.arrowMeshes) {
      gl.deleteBuffer(m.vbo)
      gl.deleteBuffer(m.ibo)
    }
    this.arrowMeshes = []
    if (this.routeMesh) {
      gl.deleteBuffer(this.routeMesh.vbo)
      gl.deleteBuffer(this.routeMesh.ibo)
      this.routeMesh = null
    }
    for (const m of this.gizmoMeshes) {
      gl.deleteBuffer(m.mesh.vbo)
      gl.deleteBuffer(m.mesh.ibo)
    }
    this.gizmoMeshes = []
    if (this.program) gl.deleteProgram(this.program)
    this.program = null
  }

  // ————— GL —————

  private setupGL(): void {
    const gl = this.gl
    this.program = linkProgram(gl, VS_MAIN, FS_MAIN)
    this.uMVP = gl.getUniformLocation(this.program, 'uMVP')
    this.uOpacity = gl.getUniformLocation(this.program, 'uOpacity')
    this.aPos = gl.getAttribLocation(this.program, 'aPos')
    this.aColor = gl.getAttribLocation(this.program, 'aColor')
    gl.enable(gl.DEPTH_TEST)
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)
    gl.clearColor(0.9, 0.89, 0.87, 1)
  }

  // ————— دوربین —————

  /** دوربین را روی کل کادر می‌نشاند — ورود اول به ۳بعدی. */
  frameAll(): void {
    if (!this.frame) return
    this.camTarget = [this.frame.widthKm / 2, this.frame.heightKm / 2, 0.8]
    this.camDist = Math.max(this.frame.widthKm, this.frame.heightKm) * 0.95
    this.camYaw = -Math.PI / 4
    this.camPitch = 0.95
    // کاربر نمای «کادر» را با دکمهٔ صریح خواسته — دیگر «دست‌کاری‌شده» نیست
    // تا recalcهای بعدی بتوانند دوربین را سرِ جا بگذارند (قبلاً یک‌بار
    // userMoved می‌رفت و دیگر هیچگاه reset نمی‌شد)
    this.userMoved = false
  }

  private cameraEye(): Vec3 {
    const cp = Math.cos(this.camPitch)
    return [
      this.camTarget[0] + this.camDist * cp * Math.cos(this.camYaw),
      this.camTarget[1] + this.camDist * cp * Math.sin(this.camYaw),
      this.camTarget[2] + this.camDist * Math.sin(this.camPitch),
    ]
  }

  /** کشِ MVP — دوربین/نسبتِ دید تغییر نکرده باشد بازمحاسبه نمی‌شود.
   * قبلاً هر `projectToScreen` یک MVP کامل می‌ساخت؛ در یک فریم دهها بار
   * (برچسب‌ها + hit-test گوی + hover شیپوری) — روی دستگاهِ ضعیف لرزش
   * می‌داد. کال‌ها فقط می‌خوانند، پس برگرداندنِ همان آبجکت امن است. */
  private mvpCache:
    | { mvp: Mat4; aspect: number; yaw: number; pitch: number; dist: number; tx: number; ty: number; tz: number }
    | null = null

  /** کشِ جایگاهِ بوم روی صفحه — یکبار در هر قاب نوسازی می‌شود؛
   * `getBoundingClientRect` هر بار فراخوانی، layout را می‌شکند (هر
   * فریم ده‌ها بار). کهنگیِ حداکثر یک فریم (~۱۶ms) نامحسوس است. */
  private viewRect: { left: number; top: number; width: number; height: number } | null = null

  private computeMVP(aspect: number): Mat4 {
    const c = this.mvpCache
    if (
      c &&
      c.aspect === aspect &&
      c.yaw === this.camYaw &&
      c.pitch === this.camPitch &&
      c.dist === this.camDist &&
      c.tx === this.camTarget[0] &&
      c.ty === this.camTarget[1] &&
      c.tz === this.camTarget[2]
    ) {
      return c.mvp
    }
    const proj = mat4Perspective(FOV_RAD, aspect, 0.5, Math.max(this.camDist * 6, 200))
    const view = mat4LookAt(this.cameraEye(), this.camTarget, [0, 0, 1])
    const mvp = mat4Multiply(proj, view)
    this.mvpCache = {
      mvp,
      aspect,
      yaw: this.camYaw,
      pitch: this.camPitch,
      dist: this.camDist,
      tx: this.camTarget[0],
      ty: this.camTarget[1],
      tz: this.camTarget[2],
    }
    return mvp
  }

  // ————— حلقهٔ رندر —————

  /** راه‌اندازی GL و حلقهٔ raf — پس از initTerrain/rebuildDynamic. ایده‌مپوتنت:
   *  اگر حلقه از قبل زنده است دوباره حلقه نمی‌سازد (بازگشت از حالت مخفی). */
  start(): void {
    if (!this.program) this.setupGL()
    if (this.rafId) return
    const tick = (): void => {
      if (this.disposed) return
      this.renderFrame()
      this.rafId = requestAnimationFrame(tick)
    }
    this.rafId = requestAnimationFrame(tick)
  }

  /** توقف حلقهٔ رندر — صحنه مخفی است؛ داده‌ها و بافرها دست‌نخورده می‌مانند. */
  pause(): void {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId)
      this.rafId = 0
    }
  }

  private renderFrame(): void {
    if (!this.program || !this.terrain) return
    const gl = this.gl
    const canvas = this.canvas
    // کشِ جایگاهِ بوم — یکبار در قاب (projectToScreen/pick همه از این می‌خوانند)
    this.viewRect = canvas.getBoundingClientRect()
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const w = Math.max(1, Math.floor(canvas.clientWidth * dpr))
    const h = Math.max(1, Math.floor(canvas.clientHeight * dpr))
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w
      canvas.height = h
      gl.viewport(0, 0, w, h)
    }
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT)
    const mvp = this.computeMVP(w / h)
    gl.useProgram(this.program)
    gl.uniformMatrix4fv(this.uMVP, false, mvp)
    gl.uniform1f(this.uOpacity, 1)
    const bindAttribs = (vbo: WebGLBuffer): void => {
      gl.bindBuffer(gl.ARRAY_BUFFER, vbo)
      gl.enableVertexAttribArray(this.aPos)
      gl.vertexAttribPointer(this.aPos, 3, gl.FLOAT, false, 24, 0)
      gl.enableVertexAttribArray(this.aColor)
      gl.vertexAttribPointer(this.aColor, 3, gl.FLOAT, false, 24, 12)
    }
    // — زمین: فقط کاشی‌های داخل مخروط دید («فقط بخشِ جلوی دوربین») —
    bindAttribs(this.terrain.vbo)
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.terrain.ibo)
    const indexType = this.terrain.bytesPerIndex === 4 ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT
    for (const tile of this.terrainTiles) {
      if (!aabbVisible(mvp, tile.bounds)) continue
      gl.drawElements(gl.TRIANGLES, tile.count, indexType, tile.start * this.terrain.bytesPerIndex)
    }
    // — پیکان‌های باد لایه‌ها (مثلث‌های توپُر) —
    gl.uniform1f(this.uOpacity, 0.95)
    for (const mesh of this.arrowMeshes) {
      bindAttribs(mesh.vbo)
      gl.drawArrays(mesh.mode, 0, mesh.indexCount)
    }
    // — لولهٔ مسیر —
    if (this.routeMesh) {
      gl.uniform1f(this.uOpacity, 1)
      bindAttribs(this.routeMesh.vbo)
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.routeMesh.ibo)
      gl.drawElements(gl.TRIANGLES, this.routeMesh.indexCount, gl.UNSIGNED_SHORT, 0)
    }
    // — ستون‌های نشانگر مبدأ/مقصد/چک‌پوینت —
    gl.uniform1f(this.uOpacity, 0.9)
    for (const mesh of this.markerMeshes) {
      bindAttribs(mesh.vbo)
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, mesh.ibo)
      gl.drawElements(gl.TRIANGLES, mesh.indexCount, gl.UNSIGNED_SHORT, 0)
    }
    // — گیمبال ویرایش نقطه — آخر (روی همه چیز)، بدون عمق برای دیده‌شدن همیشگی؛
    // محورِ زیر نشانگر (یا در حال کشیدن) پررنگ، بقیه کم‌نور — بازخورد هاور/درگ.
    if (this.gizmoMeshes.length > 0) {
      gl.disable(gl.DEPTH_TEST)
      for (const g of this.gizmoMeshes) {
        const active = this.dragAxis !== null ? g.axis === this.dragAxis : g.axis === this.hoverAxis
        gl.uniform1f(this.uOpacity, active ? 1 : 0.4)
        bindAttribs(g.mesh.vbo)
        gl.drawArrays(g.mesh.mode, 0, g.mesh.indexCount)
      }
      gl.enable(gl.DEPTH_TEST)
      gl.uniform1f(this.uOpacity, 1)
    }
    // — برچسب‌های DOMِ اعدادِ چک‌پوینت — موقعیتِ صفحه‌ایِ هر گوی در این فریم
    if (this.onMarkerScreens) {
      this.onMarkerScreens(
        this.markerDots.map((dot) => {
          const sp = this.projectToScreen(dot.posKm)
          // شعاعِ صفحه برای هر گوی خودش — گویِ دور در نمای نزدیک عمقِ
          // متفاوتی دارد؛ قبلاً از گویِ اول (مبدأ) وام می‌گرفت
          const rPx =
            sp && !sp.behind
              ? this.screenLenPx(dot.posKm, [
                  dot.posKm[0] + this.markerDotRadiusKm,
                  dot.posKm[1],
                  dot.posKm[2],
                ])
              : 0
          return {
            target: dot.target,
            x: sp?.x ?? 0,
            y: sp?.y ?? 0,
            behind: !sp || sp.behind,
            rPx,
          }
        }),
      )
    }
  }

  /** پرواز نرم دوربین به نقطهٔ جغرافیایی — برای دکمهٔ «کادر روی مسیر». */
  flyTo(lat: number, lon: number, distKm = 60): void {
    if (!this.frame) return
    const [x, y] = lonLatToKm(this.frame, lon, lat)
    this.camTarget = [x, y, this.camTarget[2]]
    this.camDist = Math.min(Math.max(distKm, 20), 600)
  }

  /** نمای کلی — کل کادر (مثل fitBounds). */
  frameOverview(): void {
    this.frameAll()
  }

  // ————— ویرایشگر نقطه (گیمبال سه‌محوره) —————

  /**
   * گیمبال را روی یک نقطه نشان می‌دهد — مختصات جغرافیایی هدف. فراخوانی
   * مجدد با هدف دیگر گیمبال را جابه‌جا می‌کند؛ با null پنهان می‌شود.
   */
  setEditTarget(
    target: EditTarget | null,
    coord: { lat: number; lon: number; alt?: number } | null,
  ): void {
    // اکوی همان درگِ تازه: صفحه پس از drop همان lat/lon را برمی‌گرداند.
    // موقعیت صحنه‌ای (به‌ویژه z پس از کشیدن محور «ارتفاع» یا z موجود روی
    // شیب) دست‌نخورده می‌ماند — بازمحاسبه از ارتفاعِ زمین نقطه را روی
    // شیب «پایین می‌پراند» و حس پرش تصادفی می‌داد.
    const echo =
      target !== null &&
      coord !== null &&
      this.editPosKm !== null &&
      this.lastEditReport !== null &&
      target.kind === this.lastEditReport.target.kind &&
      target.index === this.lastEditReport.target.index &&
      Math.abs(coord.lat - this.lastEditReport.lat) < 1e-9 &&
      Math.abs(coord.lon - this.lastEditReport.lon) < 1e-9
    this.lastEditReport = null
    if (echo) return
    this.editTarget = target
    if (!target || !coord || !this.frame || !this.terrainData) {
      this.editPosKm = null
      this.editPriorAltM = undefined
      this.dragAxis = null
      this.hoverAxis = null
      this.rebuildGizmo()
      return
    }
    // ارتفاعِ سفارشیِ معتبر — فقط وقتی صفحه حقیقتاً alt ذخیره‌شده دارد
    // (نکته: صحنهٔ خودش altM از z می‌سازد و نباید اینجا قاطی شود؛ همانی
    // که صفحه فرستاده مرجع است)
    this.editPriorAltM = coord.alt
    const [x, y] = lonLatToKm(this.frame, coord.lon, coord.lat)
    const groundM = terrainElevationAt(this.terrainData, coord.lat, coord.lon)
    // ارتفاع هدف: مقدار ذخیره‌شده (کشیدن قبلی محور «ارتفاع») یا سطح زمین؛
    // بیرونِ کادرِ زمین سطحِ دیدِ کاربر همان صفحهٔ تراز است (نه ارتفاعِ
    // چسبیدهٔ لبه) تا گیزمو روی خودِ گوی بنشیند نه بالای آن.
    const altM = coord.alt ?? (isInTerrainFrame(this.terrainData, coord.lat, coord.lon) ? groundM : 0)
    this.editPosKm = [x, y, (altM / 1000) * VERTICAL_EXAGGERATION]
    this.dragAxis = null
    this.hoverAxis = null
    this.rebuildGizmo()
  }

  /** بازسازی مش‌های گیمبال از موقعیت فعلی هدف. */
  private rebuildGizmo(): void {
    const gl = this.gl
    for (const m of this.gizmoMeshes) {
      gl.deleteBuffer(m.mesh.vbo)
      gl.deleteBuffer(m.mesh.ibo)
    }
    this.gizmoMeshes = []
    this.lastGizmoDist = this.camDist
    if (!this.editPosKm || !this.editTarget) return
    const len = Math.max(this.camDist * 0.16, GIZMO_ARROW_KM * 0.35)
    for (const spec of GIZMO_AXES) {
      const { positions, colors } = buildGizmoArrow(this.editPosKm, spec.dir, spec.rgb, len)
      this.gizmoMeshes.push({ mesh: uploadTriangles(gl, positions, colors), axis: spec.axis })
    }
  }

  /** فاصلهٔ صفحه‌ای نقطهٔ صحنه تا مختصات صفحه — برای hit-test پیکان‌ها. */
  private projectToScreen(p: Vec3): { x: number; y: number; behind: boolean } | null {
    if (!this.frame) return null
    // کشِ rect — از هر فریم؛ اگر حلقه نایستاده رزرو برای اولین فراخوانی
    // پیش از اولین رندر، یک خواندنِ مستقیم.
    const rect = this.viewRect ?? (this.viewRect = this.canvas.getBoundingClientRect())
    if (rect.width === 0 || rect.height === 0) return null
    const mvp = this.computeMVP(rect.width / rect.height)
    const cx = mvp[0] * p[0] + mvp[4] * p[1] + mvp[8] * p[2] + mvp[12]
    const cy = mvp[1] * p[0] + mvp[5] * p[1] + mvp[9] * p[2] + mvp[13]
    const cw = mvp[3] * p[0] + mvp[7] * p[1] + mvp[11] * p[2] + mvp[15]
    if (cw <= 0) return { x: 0, y: 0, behind: true }
    return {
      x: rect.left + ((cx / cw) * 0.5 + 0.5) * rect.width,
      y: rect.top + (0.5 - (cy / cw) * 0.5) * rect.height,
      behind: false,
    }
  }

  /** نزدیک‌ترین پیکان گیمبال به نشانگر — null اگر هیچ‌کدام در شعاع نیست. */
  private pickGizmoAxis(px: number, py: number): GizmoAxis | null {
    if (!this.editPosKm || !this.editTarget) return null
    // شعاع گرفتن — نسبت ثابتی از طول فلش روی صفحه + کف مطلق؛ مستقل از زوم
    // (فرمول قدیمی با مقیاس کیلومتری در نمای کلی ~۱۳۰px می‌شد و کلیکِ گوی
    // نشانگر را می‌بلعید).
    const arrowLen = Math.max(this.camDist * 0.16, GIZMO_ARROW_KM * 0.35)
    const lenPx = this.screenLenPx(this.editPosKm, [
      this.editPosKm[0] + arrowLen,
      this.editPosKm[1],
      this.editPosKm[2],
    ])
    const hitPx = Math.max(14, lenPx * 0.22)
    // فشار درستِ روی مبدأِ گیمبال: «کشیدنِ محور» بی‌معناست — قبلاً هر سه
    // محور از t=0 (مبدأ مشترک) نمونه می‌گرفتند و فشارِ مرکز همیشه «شرق–غرب»
    // را می‌گرفت و نقطه به کنار می‌پرید. مرکز = گوی/جای‌ایستادن.
    const originSp = this.projectToScreen(this.editPosKm)
    if (
      originSp &&
      !originSp.behind &&
      Math.hypot(px - originSp.x, py - originSp.y) < Math.max(8, hitPx * 0.22)
    ) {
      return null
    }
    let best: GizmoAxis | null = null
    let bestScore = Infinity
    for (const spec of GIZMO_AXES) {
      // نمونه‌گیری در طول بدنهٔ فلش — از ۱/۶ تا نوک؛ مبدأ مشترک حذف شد
      let axisBest = Infinity
      for (let s = 1; s <= 6; s += 1) {
        const t = s / 6
        const sp = this.projectToScreen([
          this.editPosKm[0] + spec.dir[0] * arrowLen * t,
          this.editPosKm[1] + spec.dir[1] * arrowLen * t,
          this.editPosKm[2] + spec.dir[2] * arrowLen * t,
        ])
        if (!sp || sp.behind) continue
        const d = Math.hypot(sp.x - px, sp.y - py)
        if (d < axisBest) axisBest = d
      }
      if (axisBest === Infinity) continue
      // جریمهٔ جهتنایی — فلشِ روبه‌جلوِ محورِ دیگر نباید فشارهای مایل را
      // قاپ بدهد: جهتِ محور روی صفحه با جهتِ فشار مقایسه و امتیاز منفی
      // هم‌جهتی نزدیک صفر بدتر رتبه‌بندی می‌شود.
      if (originSp && !originSp.behind) {
        const tipSp = this.projectToScreen([
          this.editPosKm[0] + spec.dir[0] * arrowLen,
          this.editPosKm[1] + spec.dir[1] * arrowLen,
          this.editPosKm[2] + spec.dir[2] * arrowLen,
        ])
        if (tipSp && !tipSp.behind) {
          const vx = tipSp.x - originSp.x
          const vy = tipSp.y - originSp.y
          const vl = Math.hypot(vx, vy)
          const pvx = px - originSp.x
          const pvy = py - originSp.y
          const pl = Math.hypot(pvx, pvy)
          if (vl > 1e-3 && pl > 1e-3) {
            const dot = (vx / vl) * (pvx / pl) + (vy / vl) * (pvy / pl)
            axisBest += (1 - Math.max(0, dot)) * hitPx
          }
        }
      }
      if (axisBest < bestScore) {
        bestScore = axisBest
        best = spec.axis
      }
    }
    return bestScore <= hitPx ? best : null
  }

  /** طول صفحه‌ای (پیکسل) بردار صحنه‌ای — برای شعاع گرفتن مستقل از زوم. */
  private screenLenPx(a: Vec3, b: Vec3): number {
    const sa = this.projectToScreen(a)
    const sb = this.projectToScreen(b)
    if (!sa || !sb || sa.behind || sb.behind) return 0
    return Math.hypot(sb.x - sa.x, sb.y - sa.y)
  }

  /**
   * حرکت نقطهٔ در حال ویرایش روی یک محور — دلتای صفحه → دلتای صحنه.
   * مقیاس: بردار صفحهٔ محورِ «یک کیلومتر صحنه» ساخته می‌شود؛ نسبت جابه‌جایی
   * صفحهٔ کاربر به طول همان بردار، جابه‌جایی بر حسب کیلومتر صحنه می‌دهد.
   * (بردارِ یک‌کیلومتری از projectToScreen(پیکان در جهت محور) نتیجه می‌شود —
   * همان تبدیلی که خود صحنه برای نمایش استفاده می‌کند؛ بدون فیت فاکتور دستی.)
   */
  private dragEditPoint(dxPx: number, dyPx: number): void {
    if (!this.editPosKm || !this.dragAxis || !this.dragStartPosKm || !this.frame) return
    const spec = GIZMO_AXES.find((a) => a.axis === this.dragAxis)
    if (!spec) return
    // بردار صفحه برای «یک کیلومتر صحنه» در جهت این محور
    const originSp = this.projectToScreen(this.dragStartPosKm)
    const unitSp = this.projectToScreen([
      this.dragStartPosKm[0] + spec.dir[0],
      this.dragStartPosKm[1] + spec.dir[1],
      this.dragStartPosKm[2] + spec.dir[2],
    ])
    if (!originSp || !unitSp || originSp.behind || unitSp.behind) return
    const axisScreen = [unitSp.x - originSp.x, unitSp.y - originSp.y]
    const axisLenPx = Math.hypot(axisScreen[0], axisScreen[1])
    if (axisLenPx < 1e-6) return
    // جابه‌جایی صفحه در راستای محور (پیکسل) → کیلومتر صحنه.
    // دقت: ضرب داخلی با بردارِ «یک کیلومتر» (طول L پیکسل) خودش L را در خود
    // دارد — تقسیم روی L² است، نه L؛ وگرنه حرکت ~L برابرِ حرکت ماوس می‌شد
    // (حساسیت شدید در نمای کلی).
    const alongPx = dxPx * axisScreen[0] + dyPx * axisScreen[1]
    const moveKm = alongPx / (axisLenPx * axisLenPx)
    this.editPosKm = [
      this.dragStartPosKm[0] + spec.dir[0] * moveKm,
      this.dragStartPosKm[1] + spec.dir[1] * moveKm,
      Math.min(
        Math.max(0, this.dragStartPosKm[2] + spec.dir[2] * moveKm),
        (WIND_ALTITUDE_MAX / 1000) * VERTICAL_EXAGGERATION,
      ),
    ]
    this.rebuildGizmo()
  }

  // ————— تعامل —————

  private attachEvents(): void {
    this.canvas.addEventListener('pointerdown', this.onPointerDown)
    window.addEventListener('pointermove', this.onPointerMove)
    window.addEventListener('pointerup', this.onPointerUp)
    this.canvas.addEventListener('wheel', this.onWheel, { passive: false })
  }

  private onPointerDown = (e: PointerEvent): void => {
    // — گیمبال: کلیک روی یک پیکان = شروع کشیدن همان محور (اولویت با گیمبال) —
    if (!e.shiftKey && e.button === 0) {
      const axis = this.pickGizmoAxis(e.clientX, e.clientY)
      if (axis && this.editPosKm) {
        this.dragAxis = axis
        this.dragStartScreen = { x: e.clientX, y: e.clientY }
        this.dragStartPosKm = [...this.editPosKm] as Vec3
        this.pointerDown = true
        this.panMode = false
        this.lastX = e.clientX
        this.lastY = e.clientY
        this.dragMoved = false
        return
      }
    }
    this.pointerDown = true
    this.lastX = e.clientX
    this.lastY = e.clientY
    this.dragStartScreen = { x: e.clientX, y: e.clientY }
    this.dragMoved = false
    this.panMode = e.shiftKey || e.button === 1
  }

  /** کلیک (بدون کشیدن) روی گوی نشانگر؟ — نزدیک‌ترین گوی در شعاع پیکسل. */
  private pickMarkerDot(px: number, py: number): EditTarget | null {
    if (this.markerDots.length === 0) return null
    // شعاع گرفتن = شعاع رسم گوی روی صفحه + حاشیه؛ کف ۱۸px برای نمای خیلی دور
    const refDot = this.markerDots[0]
    const dotPx = this.screenLenPx(refDot.posKm, [
      refDot.posKm[0] + this.markerDotRadiusKm,
      refDot.posKm[1],
      refDot.posKm[2],
    ])
    const hitPx = Math.max(18, dotPx + 8)
    let best: EditTarget | null = null
    let bestDist = Infinity
    for (const dot of this.markerDots) {
      const sp = this.projectToScreen(dot.posKm)
      if (!sp || sp.behind) continue
      const d = Math.hypot(sp.x - px, sp.y - py)
      if (d < bestDist) {
        bestDist = d
        best = dot.target
      }
    }
    return bestDist <= hitPx ? best : null
  }

  private onPointerMove = (e: PointerEvent): void => {
    // — حالت «افزودن چک‌پوینت» — همیشه crosshair؛ هاور عادی بی‌اثر است.
    if (this.placingPoint) {
      this.canvas.style.cursor = 'crosshair'
    } else if (!this.pointerDown && this.editTarget) {
      this.hoverAxis = this.pickGizmoAxis(e.clientX, e.clientY)
      this.canvas.style.cursor = this.hoverAxis ? 'grab' : ''
    } else if (!this.pointerDown && !this.editTarget) {
      // — هاور روی گوی نشانگر: نشانگر کلیک —
      const overDot = this.pickMarkerDot(e.clientX, e.clientY) !== null
      this.canvas.style.cursor = overDot ? 'pointer' : ''
    }
    if (!this.pointerDown) return
    const dx = e.clientX - this.lastX
    const dy = e.clientY - this.lastY
    // کشیدنِ واقعی با جابه‌جایی انباشته از نقطهٔ نشست تشخیص داده می‌شود —
    // پیشتر هر لرزشِ تک‌رویدادِ بیش از ۳px کلیک را دور می‌ریخت و کلیکِ
    // واقعی کاربر با لرزش دست (تا‌چ‌پد/موس) بی‌صدا ناموفق می‌شد.
    const down = this.dragStartScreen
    if (down && Math.hypot(e.clientX - down.x, e.clientY - down.y) > 8) this.dragMoved = true
    this.lastX = e.clientX
    this.lastY = e.clientY
    if (this.dragAxis) {
      // کشیدن پیکان — نقطه فقط روی همان محور حرکت می‌کند؛ دوربین ثابت
      const totalDx = e.clientX - (this.dragStartScreen?.x ?? e.clientX)
      const totalDy = e.clientY - (this.dragStartScreen?.y ?? e.clientY)
      this.dragEditPoint(totalDx, totalDy)
      return
    }
    if (this.panMode) {
      // جابه‌جایی هدف — dx حرکت افقی صفحه → راست‌بردار دید، dy عمودی →
      // بردار رو به جلو؛ علامت‌ها جوری که نقشه زیر انگشت سُر بخورد
      const s = this.camDist * 0.0016
      const cos = Math.cos(this.camYaw)
      const sin = Math.sin(this.camYaw)
      // راست‌بردار دید در صفحهٔ زمین: (sin, -cos)؛ جلوبردار: (cos, sin)
      this.camTarget[0] += sin * dx * s - cos * dy * s
      this.camTarget[1] += -cos * dx * s - sin * dy * s
    } else {
      this.camYaw -= dx * 0.005
      this.camPitch = Math.min(Math.max(this.camPitch + dy * 0.005, 0.12), 1.45)
    }
    this.userMoved = true
  }

  private onPointerUp = (e: PointerEvent): void => {
    if (!this.pointerDown) return
    this.pointerDown = false
    // — رها کردن پیکان گیمبال: گزارش مختصات نهایی به صفحه —
    if (this.dragAxis) {
      const axis = this.dragAxis
      this.dragAxis = null
      this.dragStartScreen = null
      this.dragStartPosKm = null
      const target = this.editTarget
      if (target && this.editPosKm && this.frame && this.onPointEdit) {
        // مختصاتِ خالص — بدون altM. قبلاً editPosLatLon همیشه altMِ محاسبه‌
        // شده از z را داخل آبجکتِ coord می‌فرستاد و به آبجکتِ چک‌پوینتِ استور
        // نشت می‌کرد؛ ارتفاعِ معنی‌دارِ صریح فقط پایین (محور ارتفاع / حفظِ
        // ارتفاعِ سفارشی) به گزارش گره می‌خورد.
        const [lon, lat] = kmToLonLat(this.frame, this.editPosKm[0], this.editPosKm[1])
        const coord = { lat, lon }
        let reportTarget: EditTarget = target
        const groundM =
          this.terrainData && isInTerrainFrame(this.terrainData, lat, lon)
            ? terrainElevationAt(this.terrainData, lat, lon)
            : 0
        if (axis === 'up') {
          // محور «ارتفاع»: ارتفاع نهایی = z اغراق‌شدهٔ صحنه → متر MSL؛
          // کف = زمین + ۲۰۰ متر (معادل قید رسم صحنه) تا نشانگر زیرِ زمین نرود.
          // پیشتر گزارشِ ارتفاع به «نزدیک‌ترین سطح پرواز» اسنپ می‌شد و کاربر
          // عملاً نمی‌توانست چک‌پوینت را وسطِ دل لایه‌ها بگذارد — ارتفاع آزاد
          // است؛ موتور در همان ارتفاع لایهٔ باد واقعی می‌سازد.
          const altM = Math.round(
            Math.max((this.editPosKm[2] / VERTICAL_EXAGGERATION) * 1000, groundM + 200),
          )
          reportTarget = { ...target, altM }
        } else if (this.editPriorAltM !== undefined) {
          // درگِ افقیِ نقطه‌ای که کاربر ارتفاعِ پروازش را تنظیم کرده — سطحِ
          // پرواز باید بماند (فقط کفِ زمینِ مکانِ تازه رعایت شود)؛ قبلاً
          // ارتفاع پاک می‌شد و CP بی‌صدا به زمین می‌چسبید.
          const heldAltM = Math.round(Math.max(this.editPriorAltM, groundM + 200))
          reportTarget = { ...target, altM: heldAltM }
        }
        // اکو: این گزارش نگه داشته می‌شود تا setEditTarget بعدی (همان
        // lat/lon) موقعیت صحنه‌ای — و z کشیده‌شده — را بازننویسی نکند.
        this.lastEditReport = { target, lat: coord.lat, lon: coord.lon }
        this.onPointEdit(reportTarget, coord)
      }
      this.canvas.style.cursor = ''
      return
    }
    // — کلیک بدون کشیدن روی گوی نشانگر: انتخاب همان نقطه برای گیمبال —
    if (!this.dragMoved) {
      const picked = this.pickMarkerDot(e.clientX, e.clientY)
      // با حالت «افزودن چک‌پوینت» فعال، کلیک روی گوی هم به ثبت نقطه می‌رود:
      // گویِ زیرِ کلیک نباید گیمبال را باز کند و حالتِ «کلیک = ثبت» را منحرف
      // سازد؛ گیمبال فقط بسته می‌شود.
      if (picked && !this.placingPoint) {
        this.onPointPick?.(picked)
        return
      }
      // کلیک خالی — هم انتخاب گیمبال را می‌بندد و هم به صفحه گزارش می‌شود
      this.onPointPick?.(null)
    }
    if (!this.dragMoved && this.onMapClick) {
      // نقشِ پذیرش: «افزودن چک‌پوینت» دشتِ دورِ مقیاس‌شده را هم می‌گیرد؛
      // مبدأ/مقصد با سقفِ سرانگیزِ کمتر (مبدأِ دور مسیرِ بنجل می‌سازد)
      const hit = this.pickLatLon(e.clientX, e.clientY, this.placingPoint ? 'checkpoint' : 'anchor')
      if (hit) this.onMapClick(hit.lat, hit.lon)
      else if (this.placingPoint) this.onPickMiss?.(this.lastPickMiss ?? 'outside')
    }
  }

  private onWheel = (e: WheelEvent): void => {    e.preventDefault()
    const factor = Math.exp(e.deltaY * 0.0012)
    this.camDist = Math.min(Math.max(this.camDist * factor, 15), 900)
    this.userMoved = true
    // بازسازی فلش‌های گیمبال فقط با تغییرِ محسوسِ فاصله (٪۳) — قبلاً هر
    // رویدادِ wheel سه مش را از صفر می‌ساخت و دوباره در GPU می‌کاشت.
    if (
      this.editTarget &&
      (this.gizmoMeshes.length === 0 ||
        this.lastGizmoDist === 0 ||
        Math.abs(this.camDist - this.lastGizmoDist) > this.lastGizmoDist * 0.03)
    ) {
      this.rebuildGizmo()
    }
  }

  /**
   * پرتاب پرتو از دوربین به صحنه — برخورد با **سطح زمین** (با اغراق عمودی)،
   * نه صفحهٔ تخت z=0؛ وگرنه کلیک روی پهنهٔ مرتفع، نقطهٔ جابه‌جاشده می‌داد.
   * ray-march + دوبخشی؛ اگر پرتو به زمین نخورد (بیرون کادر) صفحهٔ z=0.
   */
  pickLatLon(px: number, py: number, role: 'checkpoint' | 'anchor' = 'anchor'): { lat: number; lon: number } | null {
    if (!this.frame) return null
    const rect = this.viewRect ?? (this.viewRect = this.canvas.getBoundingClientRect())
    if (rect.width === 0 || rect.height === 0) return null
    const nx = ((px - rect.left) / rect.width) * 2 - 1
    const ny = 1 - ((py - rect.top) / rect.height) * 2
    const mvp = this.computeMVP(rect.width / rect.height)
    const inv = invertMat4(mvp)
    const unproj = (zClip: number): Vec3 => {
      const x = inv[0] * nx + inv[4] * ny + inv[8] * zClip + inv[12]
      const y = inv[1] * nx + inv[5] * ny + inv[9] * zClip + inv[13]
      const z = inv[2] * nx + inv[6] * ny + inv[10] * zClip + inv[14]
      const w = inv[3] * nx + inv[7] * ny + inv[11] * zClip + inv[15]
      return [x / w, y / w, z / w]
    }
    const near = unproj(-1)
    const far = unproj(1)
    const fr = this.frame
    const accept = (x: number, y: number, kind: 'march' | 'plane' = 'march'): { lat: number; lon: number } | null => {
      // پذیرش: کادرِ مجاز (زمین ∪ مسیر ∪ نشانگرها + حاشیه). برای برخوردِ
      // واقعی با سطح زمین حاشیهٔ ثابتِ کوچک (۸ ک.م) کافی است؛ ولی «صفحهٔ
      // تخت» با مقیاسِ دیدِ کاربر باید پذیرفته شود — با زومِ دورتر همان
      // پیکسلِ دشتِ اطراف به نقطهٔ دورتری می‌افتد (در camDist=۶۰۰ تا
      // ~۵۴۰ ک.م اندازه‌گیری شد)، پس حاشیهٔ آن با فاصلهٔ دوربین مقیاس
      // می‌گیرد و سقفِ مضحکِ افق (بسیار دورتر از دید) همچنان صادقانه
      // با «بیرون از کادر داده» رد می‌شود.
      const b = this.pickBoundsKm
      if (!b) return null
      // گاردِ NaN/بی‌نهایت: ماتریسِ degenerate یا پرتوِ افقیِ سرحدی
      // قبلاً می‌توانست مختصاتِ بیمعنا بسازد که همهٔ مقایسه‌های کادر را
      // «false» رد می‌کرد و از گیت می‌گذشت؛ حالا صریحاً مردود.
      if (!Number.isFinite(x) || !Number.isFinite(y)) {
        this.lastPickMiss = 'outside'
        return null
      }
      const pad =
        kind === 'plane'
          ? role === 'checkpoint'
            ? Math.max(PLANE_PICK_PAD_KM, this.camDist * 1.1)
            // مبدأ/مقصد: دشتِ نزدیک آزاد است ولی سقفِ سرانگیزِ کمتر —
            // مبدأِ صدها ک.م دور مسیرِ بنجلِ بلند می‌سازد و شگفتزده می‌کند
            : Math.max(60, this.camDist * 0.4)
          : MARCH_PICK_PAD_KM
      if (x < b.minX - pad || x > b.maxX + pad || y < b.minY - pad || y > b.maxY + pad) {
        this.lastPickMiss = 'outside'
        return null
      }
      const [lon, lat] = kmToLonLat(fr, x, y)
      return { lat, lon }
    }
    // — برخورد پرتو با سطح زمین —
    const terrain = this.terrainData
    if (terrain) {
      const at = (t: number): Vec3 => [        near[0] + t * (far[0] - near[0]),
        near[1] + t * (far[1] - near[1]),
        near[2] + t * (far[2] - near[2]),
      ]
      const groundZ = (p: Vec3): number | null => {
        const [lon, lat] = kmToLonLat(fr, p[0], p[1])
        // بیرونِ کادرِ داده «بدون زمین» است — نه فلاتِ ادامه‌دارِ ارتفاعِ لبه
        // (terrainElevationAt بیرون را به لبه می‌چسباند)؛ وگرنه پرتوِ برداشت
        // با دشتِ بی‌انتها که در رندر اصلاً رسم نمی‌شود برخورد می‌کرد و
        // کلیکِ دشتِ اطراف در زوم، برخوردِ خیالیِ دور و ردِ «بیرون از کادر»
        // می‌داد. null یعنی این نمونه زمین ندارد و پرتو از آن رد می‌شود.
        if (!isInTerrainFrame(terrain, lat, lon)) return null
        return (terrainElevationAt(terrain, lat, lon) / 1000) * VERTICAL_EXAGGERATION
      }
      // کادرِ مطلقِ زمین (ک.م، + حاشیهٔ ۲۰ ک.م برای گذرِ دوبخشی از لبه) —
      // پرتو مستقیم است و در هر محور یکنوا؛ اگر از کادر گذشت، دیگر هرگز
      // برنمی‌گردد → مارش زودهنگام تمام (قبلاً تا صفحهٔ دورِ ۵۴۰۰ ک.م
      // مارشِ بی‌ثمر می‌رفت).
      const [ax, ay] = lonLatToKm(fr, terrain.lons[0], terrain.lats[0])
      const [bx, by] = lonLatToKm(fr, terrain.lons[terrain.cols - 1], terrain.lats[terrain.rows - 1])
      const gb = {
        minX: Math.min(ax, bx) - 20, minY: Math.min(ay, by) - 20,
        maxX: Math.max(ax, bx) + 20, maxY: Math.max(ay, by) + 20,
      }
      const dxRay = far[0] - near[0]
      const dyRay = far[1] - near[1]
      // گامِ تطبیقی ~۱ ک.م — گامِ ثابتِ ۲۲۰تایی در زومِ دور تا ~۲۴ ک.م
      // باز می‌شد و کوهِ باریک از بینِ نمونه‌ها رد می‌شد (tunneling: کلیکِ
      // کوه به پشتِ کوه می‌افتاد). مقیاس تا صفحهٔ z=0 — آنجا صفحهٔ تخت
      // جایگزین مارش می‌شود و دورترش بی‌معنا.
      let spanKm = Math.hypot(far[0] - near[0], far[1] - near[1], far[2] - near[2])
      const dzRay = far[2] - near[2]
      if (dzRay < -1e-9) {
        const t0 = -near[2] / dzRay
        if (t0 < 1) spanKm *= t0
      }
      const steps = Math.min(Math.max(Math.ceil(spanKm), 240), 1600)
      let tPrev = 0
      let dPrev = groundZ(at(tPrev))
      if (dPrev !== null) dPrev = at(tPrev)[2] - dPrev
      for (let i = 1; i <= steps; i += 1) {
        const t = i / steps
        const p = at(t)
        if (
          (p[0] < gb.minX && dxRay <= 0) || (p[0] > gb.maxX && dxRay >= 0) ||
          (p[1] < gb.minY && dyRay <= 0) || (p[1] > gb.maxY && dyRay >= 0)
        ) {
          break
        }
        const g = groundZ(p)
        const d = g === null ? null : p[2] - g
        if (dPrev !== null && d !== null && dPrev > 0 && d <= 0) {
          // عبور از سطح — دوبخشی بین tPrev و t
          let lo = tPrev
          let hi = t
          for (let k = 0; k < 24; k += 1) {
            const mid = (lo + hi) / 2
            const pm = at(mid)
            const gm = groundZ(pm)
            if (gm === null || pm[2] - gm > 0) lo = mid
            else hi = mid
          }
          const hit = at((lo + hi) / 2)
          return accept(hit[0], hit[1])
        }
        tPrev = t
        dPrev = d
      }
    }
    // — جایگزین: صفحهٔ تخت z=0 (بیرون زمین یا پیش از بارگذاری DEM) —
    const dz = far[2] - near[2]
    if (Math.abs(dz) < 1e-9) {
      this.lastPickMiss = 'outside'
      return null
    }
    const t = -near[2] / dz
    // فقط پرتوِ رو به بالا (افق به بالا) مردود است — پرتویی که دشتِ بیرونِ
    // صفحهٔ دور را نشانه می‌رود هم رسا است: قبلاً t>1 مردود می‌شد و کلیکِ
    // کاربر روی همان پیش‌زمینِ دشتِ دیدنی بی‌صدا از دست می‌رفت.
    if (t < 0) {
      this.lastPickMiss = 'sky'
      return null
    }
    const x = near[0] + t * (far[0] - near[0])
    const y = near[1] + t * (far[1] - near[1])
    return accept(x, y, 'plane')
  }
}
