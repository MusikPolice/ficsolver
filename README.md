# ficsolver

A web-based factory chain planning tool for the game [Satisfactory](https://www.satisfactorygame.com/). You tell it what you want to produce and which alternate recipes you've unlocked; it enumerates every valid recipe combination, calculates machine counts and clock speeds, and compares resource consumption against your available input budget.

## What it does

- **Enumerate chains** — finds every valid combination of recipes (standard and unlocked alternates) that can produce your desired outputs, up to a configurable limit
- **Calculate quantities** — solves production rates, machine counts, and clock speeds for each chain using linear algebra; handles cyclic dependencies (e.g. aluminium water recycling)
- **Budget comparison** — compares each chain's raw resource consumption against your declared inputs and reports per-resource surplus or deficit
- **Results ranked by efficiency** — cards sorted by total resource consumption, shortest bar = most efficient; load more pages without losing previously reviewed cards
- **Failure explanations** — when no chain exists or all chains exceed your budget, the tool explains why and what's missing

## Requirements

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12.x | Backend |
| [uv](https://docs.astral.sh/uv/) | latest | Python dependency manager |
| Node.js | 20+ | Frontend build |
| [pnpm](https://pnpm.io/) | 9+ | Frontend package manager |
| Docker + Docker Compose | latest | Production deployment |
| GNU Make | any | Build orchestration (Linux/macOS/WSL) |

> **Windows note:** the Makefile targets use bash syntax and require WSL or Git Bash. PowerShell equivalents for the most common workflows are listed below.

## Getting started (development)

### 1 — Install backend dependencies

```bash
cd backend
uv sync --extra dev
```

### 2 — Install frontend dependencies

```bash
cd frontend
pnpm install
```

### 3 — Fetch game data

The backend needs `en-CA.json` from your Satisfactory install. Point `GAME_DIR` at the game's root folder (the one containing `CommunityResources/`).

**Linux / macOS / WSL / Git Bash:**
```bash
make fetch-game-data GAME_DIR=/path/to/Satisfactory
```

**PowerShell:**
```powershell
$gameDir = "C:\Program Files (x86)\Steam\steamapps\common\Satisfactory"
New-Item -ItemType Directory -Force data\game | Out-Null
Copy-Item "$gameDir\CommunityResources\Docs\en-CA.json" data\game\
```

The default Steam path on Windows is usually:
```
C:\Program Files (x86)\Steam\steamapps\common\Satisfactory
```

### 4 — Run the dev servers

Open two terminals:

```bash
# Terminal 1 — backend (hot reload)
cd backend
GAME_DATA_PATH=data/game/en-CA.json uv run uvicorn ficsolver.main:app --reload
```

```bash
# Terminal 2 — frontend (Vite dev server, proxies /api to :8000)
cd frontend
pnpm dev
```

Then open `http://localhost:5173` in your browser.

**PowerShell equivalent for the backend:**
```powershell
$env:GAME_DATA_PATH = "data/game/en-CA.json"
cd backend
uv run uvicorn ficsolver.main:app --reload
```

## Running tests

```bash
# All checks (lint + typecheck + unit tests) — run this before committing
make verify
```

Individual targets:

```bash
make lint        # Ruff (backend) + ESLint (frontend)
make typecheck   # mypy strict (backend) + tsc --noEmit (frontend)
make test        # pytest with 80% coverage gate + vitest with 80% coverage gate
```

**PowerShell equivalents:**
```powershell
# Backend
cd backend; uv run ruff check .; uv run ruff format --check .; uv run mypy src/; uv run pytest

# Frontend
cd frontend; pnpm lint; pnpm typecheck; pnpm test
```

Run a single backend test file:
```bash
cd backend && uv run pytest tests/test_solver.py -v
```

Run a single frontend test file:
```bash
cd frontend && pnpm test --reporter=verbose src/components/ChainCard.test.tsx
```

## Production deployment

### 1 — Fetch game data (if not already done)

See step 3 in Getting started above.

### 2 — Build and start

```bash
make build          # builds Docker images
docker compose up   # starts backend (:8000) and frontend nginx (:8080)
```

**PowerShell:**
```powershell
docker compose build
docker compose up
```

The app is served at `http://localhost:8080`.

### Updating game data

When Satisfactory updates, re-run `make fetch-game-data` and rebuild:

```bash
make fetch-game-data GAME_DIR=/path/to/Satisfactory
make build
docker compose up --force-recreate
```

## Project structure

```
ficsolver/
├── backend/
│   ├── src/ficsolver/
│   │   ├── main.py       # FastAPI app — /health, /items, /recipes, /solve endpoints
│   │   ├── models.py     # Dataclasses for all domain types
│   │   ├── parser.py     # en-CA.json loader and recipe extractor
│   │   ├── graph.py      # Bipartite recipe graph (NetworkX)
│   │   └── solver.py     # Two-phase solver (DFS + linear algebra)
│   └── tests/
├── frontend/
│   └── src/
│       ├── App.tsx                      # Root component, state wiring
│       ├── state.ts                     # useReducer state and actions
│       ├── api/                         # Typed API client and interfaces
│       └── components/
│           ├── SettingsPanel.tsx
│           ├── InputsPanel.tsx
│           ├── OutputsPanel.tsx
│           ├── AlternatesPanel.tsx
│           ├── ChainCard.tsx            # Individual result card
│           └── ResultsView.tsx          # Results list, pagination, failure states
├── data/
│   └── game/                            # en-CA.json and version.json (gitignored)
├── docker-compose.yml
└── Makefile
```

## API overview

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Liveness check |
| `GET /items` | All items parsed from game data |
| `GET /recipes` | All recipes (standard and alternates) |
| `POST /solve` | Run the solver; returns first page of results + `solve_id` |
| `GET /solve/{id}/results` | Fetch any page of a cached result set; supports `sort` and `page` params |

The solver accepts:
```json
{
  "inputs": { "Desc_IronIngot_C": 340 },
  "outputs": { "Desc_ModularFrame_C": 5 },
  "unlocked_alternates": ["Recipe_Alternate_IronWire_C"],
  "clocking_available": true
}
```
