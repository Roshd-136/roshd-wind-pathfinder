/**
 * تایپ‌های مشترک — معادل schemaهای `api/openapi.yaml`.
 * وقتی قرارداد API تغییر کرد، این فایل هم باید هم‌راستا به‌روز شود
 * (در آینده می‌توان با `openapi-typescript` این فایل را خودکار تولید کرد).
 */

export interface Coordinate {
  lat: number
  lon: number
}

export interface Coordinate3D extends Coordinate {
  alt: number // altitude in meters MSL
}

export type Algorithm = 'a_star' | 'dijkstra' | 'smooth' | 'wind_riding'
export type Criterion = 'time' | 'energy' | 'balanced' | 'distance' | 'safety'

/** کدام باندهای ارتفاعی لایه‌های باد روی نقشه نمایش داده شوند (فیلتر نمایش). */
export interface LayerVisibility {
  /** سطحی — باند (۰، ۱۵۰۰] متر MSL */
  surface: boolean
  /** میانی — باند (۱۵۰۰، ۲۲۰۰] متر MSL */
  mid: boolean
  /** بالا — باند (۲۲۰۰، ۲۹۰۰] متر MSL */
  high: boolean
  /** بالاترین — باند (۲۹۰۰، ۳۶۰۰] متر MSL */
  top: boolean
}

/** باند ارتفاعی انتخاب‌شده در پنل مسیر — «همه» یعنی بدون محدودیت ارتفاع. */
export type AltitudeMode = 'all' | 'surface' | 'mid' | 'high' | 'top'

export interface Checkpoint extends Coordinate {
  order?: number
  /** ارتفاع اجباری (متر MSL) — از کشیدن محور «ارتفاع» گیمبال در ۳بعدی. */
  alt?: number
}

export interface AvoidZone {
  type: 'circle'
  center: Coordinate
  radius_km: number
}

export interface RouteConstraints {
  max_wind_speed_mps?: number | null
  altitude_range_m?: [number, number] | null
  avoid_zones?: AvoidZone[]
  criterion?: Criterion
  weights?: { time: number; energy: number }
  /** پیکربندی هواپیما/وسیلهٔ نقلیه — ارسال می‌شود به بک‌اند برای محاسبه هزینه */
  vessel?: {
    type: string
    airspeed_mps: number
    induced_drag_coeff: number
    headwind_penalty_coeff: number
  }
}

export interface RouteRequest {
  origin: Coordinate
  destination: Coordinate
  checkpoints?: Checkpoint[]
  layer_mode?: 'auto' | 'manual'
  altitude_m?: number | null
  algorithm?: Algorithm
  constraints?: RouteConstraints
  async?: boolean
}

export interface RouteResult {
  route_id: string
  path: Coordinate[]
  path_3d?: Coordinate3D[]
  layer_altitude_m: number
  algorithm: Algorithm
  criterion: Criterion
  total_distance_km: number
  estimated_time_hours: number
  total_cost: number
  created_at: string
  is_saved?: boolean
  // Additional metrics from WindRouter
  total_energy_index?: number
  tailwind_leg_fraction?: number
  heading_changes?: number
  total_climb_m?: number
  total_descent_m?: number
  climb_legs?: number
  altitudes_used?: number[]
}

export interface LayerComparisonRow {
  layer_altitude_m: number
  estimated_time_hours: number
  total_distance_km: number
  total_cost: number
  is_best: boolean
}

export interface LayerComparison {
  best_altitude_m: number
  rows: LayerComparisonRow[]
}

export interface WindLayerMeta {
  altitude_m: number
  unit: string
  bbox: [number, number, number, number]
  last_updated: string
}

/** یک بردار باد روی شبکه — معادل schema `WindVector` در api/openapi.yaml. */
export interface WindVector {
  lat: number
  lon: number
  speed_mps: number
  direction_deg: number
}

/** میدان برداری باد یک لایه — معادل schema `WindField` (GET /wind-layers/{alt}/field). */
export interface WindField {
  altitude_m: number
  vectors: WindVector[]
}
