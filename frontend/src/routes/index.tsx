import 'maplibre-gl/dist/maplibre-gl.css'

import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'
import MapGL, { GeolocateControl, NavigationControl } from 'react-map-gl/maplibre'

import { ApiStatus } from '@/components/api-status'
import { LanguageToggle } from '@/components/language-toggle'
import { JAPAN_VIEW, MAP_STYLE_URL } from '@/lib/map'

export const Route = createFileRoute('/')({
  component: MapPage,
})

function MapPage() {
  const { t } = useTranslation()

  return (
    <main className="relative h-dvh w-full overflow-hidden">
      <MapGL
        initialViewState={JAPAN_VIEW}
        mapStyle={MAP_STYLE_URL}
        style={{ position: 'absolute', inset: 0 }}
      >
        <NavigationControl position="bottom-right" />
        <GeolocateControl position="bottom-right" />
      </MapGL>

      <header className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between gap-2 p-3">
        <h1 className="pointer-events-auto rounded-md bg-background/90 px-3 py-1.5 text-sm font-semibold shadow">
          {t('app.title')}
        </h1>
        <div className="pointer-events-auto flex items-center gap-2">
          {import.meta.env.DEV && <ApiStatus />}
          <LanguageToggle />
        </div>
      </header>
    </main>
  )
}
