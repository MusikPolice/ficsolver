# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ficsolver** is a web-based factory chain planning tool for the game Satisfactory. Players specify desired outputs and unlocked alternate recipes; the solver returns minimal recipe sets with machine counts, rates, and resource budgets.

## Commands

All primary workflows go through the root `Makefile`:

```bash
make verify          # lint + typecheck + test (run before committing)
make lint            # ruff check/format (backend) + pnpm lint (frontend)
make typecheck       # mypy src/ (backend) + tsc --noEmit (frontend)
make test            # pytest (backend, 80% coverage) + pnpm test (frontend, vitest)
make test-visual     # Playwright visual regression (frontend)
make ci              # full pipeline: lint → typecheck → test → test-visual → build
make build           # Docker compose build (requires game data)
make fetch-game-data GAME_DIR=/path/to/game  # extract en-CA.json from install
```

Run a single backend test file:
```bash
cd backend && uv run pytest tests/test_solver.py -v
```

Run a single frontend test:
```bash
cd frontend && pnpm test --reporter=verbose src/some.test.ts
```

Backend dev server (no Docker):
```bash
cd backend && GAME_DATA_PATH=data/game/en-CA.json uv run uvicorn ficsolver.main:app --reload
```

Frontend dev server (proxies `/api` to backend at `:8000`):
```bash
cd frontend && pnpm dev
```

## Architecture

Three-tier: React/TypeScript frontend → FastAPI backend → game data parser + solver engine.

### Backend (`backend/src/ficsolver/`)

| Module | Role |
|--------|------|
| `main.py` | FastAPI app; endpoints `/health`, `/items`, `/recipes`; `get_game_data()` cached via `@lru_cache` |
| `models.py` | All dataclasses: `Item`, `Recipe`, `Machine`, `GameData`, `SolverChain`, `BudgetComparison`, etc. |
| `parser.py` | Loads `en-CA.json` (UTF-16 LE with BOM); extracts items/recipes/machines from Unreal Engine NativeClass buckets; converts cycle-based amounts to per-minute rates |
| `graph.py` | Builds a bipartite directed graph (items ↔ recipes) using NetworkX; build-gun recipes excluded |
| `solver.py` | Two-phase solver (see below) |

**Two-phase solver:**

- **Phase 1** — DFS from desired outputs back to raw resources; enumerates minimal recipe sets (limit 200) handling alternates, byproduct routing, and cycle detection. Returns `Phase1Result` containing `list[RecipeSelection]`.
- **Phase 2** — For each `RecipeSelection`, solves production rates via back-substitution (acyclic chains) or `numpy.linalg.lstsq` (cyclic chains). Derives machine counts and clock speeds. Runs budget comparison against declared available inputs. Returns `SolverChain` with machine groups and a `BudgetComparison` per item.

### Frontend (`frontend/src/`)

| Module | Role |
|--------|------|
| `App.tsx` | Root component; `useReducer` over full app state; wires `handleSolve`, `handleLoadMore`, `handleSortChange` |
| `state.ts` | `AppState`, `Action` union, `reducer`, `initialState`, `relevantAlternates`; exports `SortKey` type |
| `api/types.ts` | TypeScript interfaces mirroring all backend Pydantic models (`Item`, `Recipe`, `SolveRequest`, `SolveResponse`, `ChainResultOut`, `BudgetEntryOut`, `SolveFailureOut`, etc.) |
| `api/client.ts` | Typed fetch-based API client: `getItems`, `getRecipes`, `postSolve`, `getSolveResults` |
| `components/SettingsPanel.tsx` | Clocking-available toggle |
| `components/InputsPanel.tsx` | Available inputs form (item + rate rows, add/remove) |
| `components/OutputsPanel.tsx` | Desired outputs form (max 10, item + rate rows) |
| `components/AlternatesPanel.tsx` | Alternate recipe checkboxes filtered to relevant outputs, sorted alphabetically |
| `components/ChainCard.tsx` | Single result card: relative resource bar (shortest = best), ⚠ deficit indicator, machine group list with ceiled clock speeds, implicit outputs, tap-to-expand budget detail table |
| `components/ResultsView.tsx` | Results container: sort selector, result count, cap-reached notice, chain cards, Load More pagination, Phase 1 and Phase 2 failure cards |

**State shape key fields:**
- `displayedResults: ChainResultOut[]` — accumulated chains across pages (appended by Load More, replaced by sort change)
- `currentSort: "resource"` — active sort key
- `isLoadingMore: boolean` — Load More in flight
- `solveResult: SolveResponse | null` — latest API response (tracks current page number and solve_id)

The Vite config proxies `/api/*` to the backend at `:8000` during development.

### Data Flow

```
User request (desired outputs + unlocked alternates)
  → parser.py loads cached en-CA.json
  → solver.py Phase 1: enumerate recipe combinations (DFS)
  → solver.py Phase 2: calculate rates & machine counts (matrix solve)
  → budget checker: per-item surplus/deficit
  → JSON response with SolverChain list
```

### Test Fixtures

Backend tests use two fixture universes defined in `backend/tests/fixtures/game_data.py`:
- `FIXTURE` — standard "Zorblax" universe for normal solver tests
- `CYCLIC_FIXTURE` — universe with production cycles for testing the lstsq path

### Deployment

Docker Compose runs both services. Backend on `:8000`, frontend nginx on `:8080`. Game data (`en-CA.json`) is baked into the backend image at build time via `make fetch-game-data`.

## Key Constraints

- Backend uses `uv` for dependency management (not pip/poetry).
- mypy runs in strict mode; all public functions require type annotations.
- 80% test coverage is enforced by both pytest and vitest — new code needs tests.
- The game data file is UTF-16 LE with BOM; the parser handles this — don't change the encoding logic without testing against a real game install.
