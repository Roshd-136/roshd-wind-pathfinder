import type { HTMLAttributes, ReactNode } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
}

/**
 * کارت پایه — الگوی پنل‌های سمت راست/کنترل در mockup: پس‌زمینه surface،
 * حاشیه ظریف، گوشه گرد، سایه ملایم.
 */
export function Card({ className = '', children, ...rest }: CardProps) {
  return (
    <div
      className={`rounded-lg border border-border bg-surface p-4 shadow-[var(--shadow-card),inset_0_1px_2px_rgba(255,255,255,0.06),inset_0_-1px_2px_rgba(0,0,0,0.18)] ${className}`}
      {...rest}
    >
      {children}
    </div>
  )
}
