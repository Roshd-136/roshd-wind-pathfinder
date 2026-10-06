import { ChevronDown } from 'lucide-react'
import { useId, useState, type ReactNode } from 'react'

interface CollapsibleProps {
  title: string
  children: ReactNode
  defaultOpen?: boolean
}

/**
 * بخش جمع‌شونده — دسته‌بندی تنظیمات پیشرفته؛ محتوا فقط وقتی کاربر خودش
 * گسترش دهد رندر می‌شود (چک‌لیست آیتم ۱۱: «فقط با گسترش دسته نمایش داده شود»).
 */
export function Collapsible({ title, children, defaultOpen = false }: CollapsibleProps) {
  const [open, setOpen] = useState(defaultOpen)
  const contentId = useId()

  return (
    <div className="rounded-md border border-border">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={contentId}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-sm font-medium text-text-primary"
      >
        {title}
        <ChevronDown
          size={15}
          aria-hidden
          className={`shrink-0 text-text-muted transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && (
        <div id={contentId} className="space-y-3 border-t border-border px-3 py-3">
          {children}
        </div>
      )}
    </div>
  )
}
