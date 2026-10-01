import { z } from 'zod'

/** منطبق با محدودیت‌های `LoginRequest`/`RegisterRequest` در api/openapi.yaml. */
export const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
})
export type LoginFormValues = z.infer<typeof loginSchema>

export const registerSchema = z.object({
  name: z.string().min(1),
  email: z.string().email(),
  password: z.string().min(8),
})
export type RegisterFormValues = z.infer<typeof registerSchema>

export const forgotPasswordSchema = z.object({
  email: z.string().email(),
})
export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>
