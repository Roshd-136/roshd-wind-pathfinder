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
      className={`rounded-lg border border-border bg-surface p-4 shadow-[var(--shadow-card)] ${className}`}
      {...rest}
    >
      {children}
    </div>
  )
}
