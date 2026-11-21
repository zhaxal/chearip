import { defineConfig } from 'orval'

// Generates TanStack Query hooks + zod schemas from the FastAPI OpenAPI document.
// The backend must be running: `npm run api:generate`.
export default defineConfig({
  chearip: {
    input: { target: process.env.OPENAPI_URL ?? 'http://localhost:8000/openapi.json' },
    output: {
      client: 'react-query',
      httpClient: 'fetch',
      mode: 'tags-split',
      target: './src/api/generated',
      schemas: { path: './src/api/generated/model', type: 'zod' },
      clean: true,
      override: {
        fetch: {
          includeHttpResponseReturnType: false,
          forceSuccessResponse: true,
          runtimeValidation: true,
        },
      },
    },
  },
})
