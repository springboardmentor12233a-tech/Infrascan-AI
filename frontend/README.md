# InfraScan Frontend

React + TypeScript + Vite + Tailwind CSS frontend for InfraScan.

## Setup & Commands

```powershell
cd frontend
npm install   # if node_modules not present
npm run dev   # start dev server on http://localhost:5173
npm run build # production TypeScript + Vite build
```

## Environment Variables (`frontend/.env`)

- `VITE_API_BASE_URL=http://localhost:8000/api/v1`
- `VITE_ENABLE_MOCK_DATA=true` (set `false` for live FastAPI backend)

