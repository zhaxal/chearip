import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'

export function LanguageToggle() {
  const { t, i18n } = useTranslation()
  const next = i18n.resolvedLanguage === 'ja' ? 'en' : 'ja'

  return (
    <Button
      variant="secondary"
      size="sm"
      aria-label={t('language.switchLabel')}
      onClick={() => void i18n.changeLanguage(next)}
    >
      {t('language.switchTo')}
    </Button>
  )
}
