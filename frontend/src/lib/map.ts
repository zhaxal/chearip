import { setWorkerUrl } from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'

// MapLibre locates its worker next to its own module; Vite's dep pre-bundling (dev) and
// chunking (build) move that module, so hand MapLibre a Vite-managed worker URL instead.
setWorkerUrl(maplibreWorkerUrl)

// OpenFreeMap: free vector tiles, no API key.
export const MAP_STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty'

export const JAPAN_VIEW = { longitude: 137.5, latitude: 37.5, zoom: 4.3 }
