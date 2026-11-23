import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from './client'

/**
 * رگرسیون دسترسی از تلفن: مقدار پیشفرض `http://localhost:8000` روی گوشی
 * یعنی «خود گوشی»، نه کامپیوتر میزبان — درخواست Failed to fetch میشد و رابط
 * به مسیر نمایشی مشهد–سبزوار سقوط میکرد. در dev مسیرها باید نسبی باشند تا
 * پراکسی هم\u200cمبدأ Vite آنها را به بک\u200cاند برساند.
 */
describe('client base URL', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({}) }),
    )
  })

  it('uses a relative /v1 path in development', async () => {
    await apiFetch('/v1/routes', { method: 'POST', body: {} })
    expect(fetch).toHaveBeenCalledWith(
      '/v1/routes',
      expect.objectContaining({ method: 'POST' }),
    )
  })
})
