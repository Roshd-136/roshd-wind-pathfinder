/**
 * تایپ‌های مشترک — معادل schemaهای `api/openapi.yaml`.
 * وقتی قرارداد API تغییر کرد، این فایل هم باید هم‌راستا به‌روز شود
 * (در آینده می‌توان با `openapi-typescript` این فایل را خودکار تولید کرد).
 */

export interface Coordinate {
  lat: number
  lon: number
}

export type Algorithm = 'a_star' | 'dijkstra'
export type Criterion = 'time' | 'energy' | 'balanced'

export interface Checkpoint extends Coordinate {
  order?: number
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
  layer_altitude_m: number
  algorithm: Algorithm
  criterion: Criterion
  total_distance_km: number
  estimated_time_hours: number
  total_cost: number
  created_at: string
  is_saved?: boolean
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

export interface WindPointSample {
  altitude_m: number
  speed_mps: number
  direction_deg: number
}
