# Face Verification Pipeline — frontend

React + TypeScript + Vite UI for the Task 3 pipeline. It is a local demo surface
for the backend at `http://localhost:8000`, not a hosted website.

```bash
npm install
npm run dev      # http://localhost:5173 (falls back to 5174/5175 if taken)
npm run build
```

`VITE_API_URL` overrides the backend origin (default `http://localhost:8000/api`).

Design system, tokens and the zero-blur shadow rule are documented in the root
`README.md`.
