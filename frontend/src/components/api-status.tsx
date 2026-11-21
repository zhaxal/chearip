import { useTranslation } from 'react-i18next'

import { useHealth } from '@/api/generated'
import { cn } from '@/lib/utils'

/** Dev-only indicator proving the generated client → proxy → FastAPI → Postgres path works. */
export function ApiStatus() {
  const { t } = useTranslation()
  const { isPending, isError } = useHealth()

  const label = isPending ? t('api.loading') : isError ? t('api.error') : t('api.ok')

  return (
    <span
      className="flex items-center gap-1.5 rounded-md bg-background/90 px-2 py-1 text-xs shadow"
      role="status"
    >
      <span
        className={cn(
          'size-2 rounded-full',
          isPending ? 'bg-muted-foreground' : isError ? 'bg-destructive' : 'bg-green-600',
        )}
      />
      {label}
    </span>
  )
}
