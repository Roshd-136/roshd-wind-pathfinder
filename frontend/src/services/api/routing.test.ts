import { afterEach, describe, expect, it, vi } from 'vitest'
import { calculateRouteWithProgress } from './routing'
import type { RouteResult } from '../../types/routing'

const RESULT: RouteResult = {
  route_id: 'r1',
  path: [],
  layer_altitude_m: 2900,
  algorithm: 'a_star',
  criterion: 'time',
  total_distance_km: 174.1,
  estimated_time_hours: 2.5,
  total_cost: 1.2,
  created_at: new Date().toISOString(),
}

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: true,
    status,
    json: async () => body,
  } as unknown as Response
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('calculateRouteWithProgress (comment 12)', () => {
  it('accepts an async job, polls progress, and resolves with the result', async () => {
    const seen: number[] = []
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ job_id: 'j1', status: 'pending' }, 202),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          status: 'running',
          progress: 40,
          result: null,
          error: null,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          status: 'completed',
          progress: 100,
          result: RESULT,
          error: null,
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    const result = await calculateRouteWithProgress(
      { origin: { lat: 0, lon: 0 }, destination: { lat: 1, lon: 1 } },
      (p) => seen.push(p),
    )

    expect(result.total_distance_km).toBe(174.1)
    // پیشرفت ۴۰٪ در poll میانی و ۱۰۰٪ در poll پایانی گزارش میشود
    expect(seen).toEqual([40, 100])
    // poll به /jobs/{id} رفته است
    const pollUrl = fetchMock.mock.calls[1]?.[0] as string
    expect(pollUrl).toContain('/v1/routes/jobs/j1')
    // بدنهٔ POST با async: true فرستاده شده
    const opts = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(JSON.parse(String(opts.body)).async).toBe(true)
  })

  it('rejects with the engine error when the job fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ job_id: 'j2', status: 'pending' }, 202),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          status: 'failed',
          progress: 5,
          result: null,
          error: 'مسیری محاسبه نشد — نقاط بسیار نزدیک',
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      calculateRouteWithProgress({
        origin: { lat: 0, lon: 0 },
        destination: { lat: 1, lon: 1 },
      }),
    ).rejects.toThrow('مسیری محاسبه نشد')
  })

  it('passes a synchronous result through unchanged (older backend)', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse(RESULT, 200))
    vi.stubGlobal('fetch', fetchMock)

    const result = await calculateRouteWithProgress({
      origin: { lat: 0, lon: 0 },
      destination: { lat: 1, lon: 1 },
    })

    expect(result.total_distance_km).toBe(174.1)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
