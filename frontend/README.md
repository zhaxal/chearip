# Chearip frontend

React + TypeScript (Vite), TanStack Router (file-based, `src/routes/`), TanStack Query,
zod, Tailwind CSS v4, shadcn/ui (Base UI), MapLibre via react-map-gl, react-i18next (en default, ja).

```bash
npm install
npm run dev            # http://localhost:5173 — proxies /api to the backend on :8000
npm run api:generate   # regenerate src/api/generated from the running backend's OpenAPI
npm run build          # production build + typecheck
npm run lint
```

Generated files — don't edit by hand:
- `src/api/generated/**` (orval: query hooks + zod schemas)
- `src/routeTree.gen.ts` (TanStack Router plugin)

UI strings live in `src/i18n/locales/{en,ja}.json`; keys are type-checked against `en.json`.
