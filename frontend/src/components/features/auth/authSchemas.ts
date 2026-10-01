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

/** منطبق با `token`/`new_password` در api/openapi.yaml (حداقل ۸ کاراکتر). */
export const resetPasswordSchema = z
  .object({
    token: z.string().min(1),
    password: z.string().min(8),
    confirmPassword: z.string().min(8),
  })
  .refine((v) => v.password === v.confirmPassword, {
    path: ['confirmPassword'],
    message: 'auth.passwordMismatch',
  })
export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>

export const verifyEmailSchema = z.object({
  token: z.string().min(1),
})
export type VerifyEmailFormValues = z.infer<typeof verifyEmailSchema>
