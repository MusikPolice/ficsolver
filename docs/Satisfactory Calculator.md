A personal, mobile-friendly web tool for planning Satisfactory factory production chains. Runs in Docker on my media server.
## Problem Statement
Satisfactory factories are directed graphs of machines. Each machine consumes inputs at fixed rates and produces outputs at fixed rates. As factories grow complex (dozens of machines, multiple alternate recipes), ad-hoc planning breaks down. Currently modeled in Excel (`./Modular Frame.xlsx`) — this tool replaces that with a proper calculator.
## Core Concepts
### Resources and Recipes
- Every item is either a **raw resource** (mined/extracted) or a **produced part** (output of a recipe)
- A **recipe** has: one machine type, one or more inputs (item + rate), one or more outputs (item + rate). All rates are per minute.
- **Alternate Recipes** are variants unlocked via tech tree progression. Multiple recipes may exist for the same output. The user specifies which alternates they've unlocked.
### The Calculation Model
- User specifies **available inputs** (e.g. 340 Iron Ingot/min) — treated as a shared budget across all requested outputs
- User specifies **desired outputs** (e.g. 5 Modular Frame/min)
	- The user may specify multiple desired outputs (maximum 10). When the requested outputs share intermediate items, the solver produces **one unified chain** — shared intermediates are counted once and resources are not double-counted. When the requested outputs share no intermediates, the solver still returns a valid result: the chains appear as independent sub-chains within the same result card, and their resource consumption is combined in the budget comparison. A result card may therefore represent two or more disconnected sub-chains.
- User specifies **unlocked alternate recipes**
- Tool computes: for each valid combination of recipes through the dependency graph, what machines are needed, at what clock speed, producing what outputs (including surplus intermediates)
- Tool compares total resource consumption against the available budget and reports the **delta** — surplus or deficit per input resource
- Tool does **not** make decisions for the player. It surfaces options and flags constraint violations.
### Budget Warnings
If a production chain requires more of an input than is available, the tool warns with the exact deficit. The player then decides whether to overclock miners, adjust target outputs, or choose a different recipe path. See spreadsheet cell B10 for a real example of this — the modeled factory requires 108 more Iron Ingots than are available.
### Machine Counts and Clock Speeds
For each machine group in a chain:
- **Count**: minimum whole number of machines needed to hit target output
- **Clock speed**: the fraction at which all machines in the group run to collectively hit the target output. 
	- Note that the in-game user interface only allows clock speed to be adjusted in whole number increments. If a clock speed like 83.33% is computed, it must be rounded up to 84%
	- **Example**: A constructor configured to produce 20 iron plates per minute consumes 30 iron ingots per minute. 
		- To produce 40 iron plates per minute, we could build two constructors that run at 100% clock speed 
		- To make 35 iron plates per minute, we would need two constructors clocked to 88%. In this configuration, each constructor will produce 17.6 iron plates per minute (for a total production of 35.2 iron plates per minute, which is greater than the requested 35) and consume 26.4 iron ingots per minute
- In general, the user prefers to underclock machines than to overclock: Overclocking requires power shards, a rare resource that is best saved for resource-producing machines like miners. This preference is naturally enforced by the count formula — `count = ceil(required / machine_rate)` always produces enough machines to meet the target at or below 100% clock speed. The solver cannot produce a result that requires overclocking.
- Note also that clocking is an unlockable ability that must be researched in the tech tree. The user should be able to specify whether clocking is supported in their factory. When `clocking_available=false`, Phase 2 runs identically — the continuous balance equations are solved and machine counts are derived via `ceil` as normal — but clock speed is always reported as 100% rather than the computed fraction. The actual output rate will therefore equal `count × machine_rate`, which is at or above the requested target. This surplus is expected and unavoidable until clocking is unlocked.
## Example: Modular Frame Factory
**Input:** 340 Iron Ingot/min
**Target output:** 5 Modular Frame/min
**Alternates used:** Stitched Iron Plate (Reinforced Iron Plate variant using Wire), Iron Wire (Wire from Iron Ingots instead of Copper Ingots)

| Machine     | Recipe                                                            | Count | Clock | Output/min |
| ----------- | ----------------------------------------------------------------- | ----- | ----- | ---------- |
| Assembler   | 3 Reinforced Iron Plate + 12 Iron Rod → 2 Modular Frame           | 3     | 84%   | 5.04       |
| Assembler   | 18.75 Iron Plate + 37.5 Wire → 3 Reinforced Iron Plate (Stitched) | 8     | 96%   | 23.04      |
| Constructor | 15 Iron Ingot → 15 Iron Rod                                       | 4     | 77%   | 46.2       |
| Constructor | 30 Iron Ingot → 20 Iron Plate                                     | 8     | 100%  | 160        |
| Constructor | 12.5 Iron Ingot → 22.5 Wire (Iron Wire alt)                       | 13    | 99%   | 289.575    |
**Side outputs:** surplus Reinforced Iron Plate, Iron Rod, Iron Plate (Wire = 0, consumed exactly)
**Budget result:** -108 Iron Ingot (deficit — factory as modeled needs more than available)
## Tech Stack

| Layer            | Choice                      | Rationale                                                                |
| ---------------- | --------------------------- | ------------------------------------------------------------------------ |
| Frontend         | React + Tailwind CSS        | Mobile-first, mature ecosystem, fast iteration                           |
| Backend          | Python + FastAPI            | Best graph/solver libraries (NetworkX, scipy), clean API layer           |
| Containerization | Docker Compose              | Single compose file: nginx (frontend) + FastAPI (backend)                |
| Recipe Data      | `CommunityResources/Docs/en-CA.json` | Shipped with the game; UTF-16 encoded; 856 recipes including alternates |
**Rejected:** Kotlin Native/KMP — interesting but immature JS compilation target, no relevant library advantage for this problem.
## Build Environment
### Python Toolchain

| Concern               | Tool                    | Notes                                                                                             |
| --------------------- | ----------------------- | ------------------------------------------------------------------------------------------------- |
| Dependency management | `uv`                    | No explicit virtualenv required; lockfile committed; `uv run` executes in the managed environment |
| Formatting + linting  | `Ruff`                  | Single tool for both; replaces Black + isort + Flake8                                             |
| Static analysis       | `mypy`                  | Strict mode; all public API surface must be typed                                                 |
| Testing               | `pytest` + `pytest-cov` | Coverage gate enforced — build fails below threshold                                              |
### Frontend Toolchain

| Concern            | Tool                          | Notes                                                                                   |
| ------------------ | ----------------------------- | --------------------------------------------------------------------------------------- |
| Package management | `pnpm`                        | Faster than npm; efficient disk usage via content-addressable store; lockfile committed |
| Dev server         | `vite dev`                    | Hot module replacement; proxies `/api` to FastAPI backend during development            |
| Formatting         | `Prettier`                    | Opinionated, zero-config; integrated with ESLint via `eslint-config-prettier`           |
| Linting            | `ESLint`                      | React + TypeScript rules; no warnings permitted in CI                                   |
| Static analysis    | `TypeScript` (`tsc --noEmit`) | Strict mode; all API response shapes typed                                              |
| Unit testing       | `Vitest`                      | Co-located test files; runs in Node, no browser required                                |
| Visual regression  | `Playwright`                  | See below                                                                               |

### Visual Regression Testing (Playwright)
Playwright starts the frontend dev server, opens a real browser, navigates to the page, and takes a screenshot. On the first run the screenshot is saved as a baseline. On subsequent runs the new screenshot is compared against the baseline pixel-by-pixel; the test fails if the diff exceeds a configurable threshold.

This catches layout regressions that unit tests cannot — broken flexbox, clipped text, missing cards, incorrect colors — without requiring a human to manually inspect the UI after every change.

**Scope for Stage 1:**
- Baseline screenshot of the empty three-panel layout (desktop and mobile viewports)
- Baseline screenshot of the Results view: multiple cards with resource consumption bars at varying fill levels, one card with an overflowing deficit bar and warning symbol, implicit outputs visible
- Baseline screenshot of the expanded detail table (card tapped)
- Baseline screenshot of Phase 1 and Phase 2 failure states

Baselines are committed to the repository. When an intentional UI change is made, baselines are regenerated with `playwright update-snapshots` and the new images are committed alongside the code change.
### Shared Build Targets (Makefile)

| Target             | What it does                                                                                         |
| ------------------ | ---------------------------------------------------------------------------------------------------- |
| `make fetch-game-data GAME_DIR=<path>` | Copies `en-CA.json` from `<path>/CommunityResources/Docs/` into `data/game/`; reads Steam build ID from `<path>/../../appmanifest_526870.acf` and writes `data/game/version.json`. Must be run before `make build` when game data has changed. |
| `make lint`        | Ruff + ESLint                                                                                        |
| `make typecheck`   | mypy + tsc                                                                                           |
| `make test`        | pytest + Vitest                                                                                      |
| `make test-visual` | Playwright screenshot tests (requires dev server running or uses Playwright's built-in server start) |
| `make build`       | Vite production build + Docker image build (requires `data/game/` to be populated)                  |
| `make ci`          | `lint` → `typecheck` → `test` → `test-visual` → `build` in sequence; this is what runs in CI         |
## Architecture
### Data Layer
- Source file: `CommunityResources/Docs/en-CA.json`, UTF-16 encoded. The old single `Docs.json` has been replaced by per-locale files; `en-CA.json` is the one we use.
- The file is sourced from the game's install directory and will be **baked into the Docker image** at build time. When the game updates, the image must be rebuilt with the new file. Game data is fetched into the project via `make fetch-game-data GAME_DIR=<path>` (see Build Environment). The script also extracts the Steam build ID from `steamapps/appmanifest_526870.acf` (two directories above the game install dir) and writes it to `data/game/version.json` alongside the recipe data. This build ID is stored as metadata, baked into the image, and displayed in the UI (e.g. "Data: Steam Build 21237829") so the user can verify it matches their installed game version. `CommunityResources/CustomVersions.json` is not used — it contains internal Unreal Engine component versions that are not meaningful to players.
- Parse into typed Python models (`Item`, `Recipe`, `Machine`), then build the recipe graph
- Store as structured JSON or SQLite
- Recipe graph: a general directed graph — **not** assumed to be acyclic. Some chains (e.g. aluminum water recycling) contain genuine cycles where a recipe's byproduct feeds back into an upstream input. Represented as a bipartite graph with two node types: items and recipes. Edges run item→recipe (consumption) and recipe→item (production).
- **Recipe format details:**
  - `mIngredients` / `mProduct` are encoded strings (not nested JSON) — Unreal Engine property text format. Well-understood and extensively documented by the Satisfactory modding community; do not reverse-engineer from scratch. Use [SatisfactoryTools](https://github.com/greeny/SatisfactoryTools) as the primary reference implementation (TypeScript, but the parsing logic is directly transferable). Other Python implementations exist on GitHub and are findable by searching for `satisfactory docs.json parser`.
  - Item identifiers are Unreal class path strings (e.g. `.../Desc_IronPlate.Desc_IronPlate_C`). These must be normalized to a stable short key consistently across ingredient lists, product lists, and item definitions — otherwise graph edges won't connect.
  - Amounts are **per-cycle**, not per-minute. Per-minute rate = `amount / (mManufactoringDuration / 60)`
  - `mProducedIn` contains the machine class path(s) that can run the recipe
- **Identifying alternates:** `ClassName` is prefixed with `Recipe_Alternate_`; `mDisplayName` is prefixed with `"Alternate: "`. No external data source needed.
- **Build cost recipes:** machine construction costs are stored in `en-CA.json` under `FGRecipe`, using the same `mIngredients`/`mProduct` format as production recipes. They are distinguished by `mProducedIn` containing `BP_BuildGun.BP_BuildGun_C` instead of a manufacturer class path. The Commit 2 parser handles the format; Stage 2 only needs to filter for build-gun recipes and associate each with its machine via `mProduct`.
- **General principle:** prefer community reference implementations over original work wherever this file's quirks are concerned. The format has been picked apart thoroughly; the risk in Commit 2 is integration and test coverage, not format discovery.
### Solver (Backend)
The solver runs in two distinct phases. Phase 1 selects recipes; Phase 2 calculates quantities. This separation correctly handles shared intermediates, diamond dependencies, and cyclic chains (e.g. aluminum water recycling) without special-casing.

**Phase 1 — Recipe selection (DFS)**
- DFS from desired output(s) back toward raw resources, traversing the recipe graph
- At each item node where multiple recipes exist (standard + unlocked alternates), branch — each branch is a separate candidate chain
- Chains must be minimal: only recipes necessary to produce the desired outputs are included. No redundant or artificially extended paths.
- Byproduct routing: when the DFS encounters an item it needs, it first checks whether that item is already produced as a byproduct by a recipe already in the current selection. If it is, the DFS does **not** seek a dedicated recipe for that item — Phase 2's balance equations will naturally account for the byproduct's production rate and compute the net shortfall (if any) as a raw resource requirement. A dedicated recipe is only sought if no byproduct in the current selection already covers the item.
- Cycle detection: if a recipe's byproduct feeds back into an upstream recipe in the same set (e.g. water in aluminum), the cycle is flagged so Phase 2 can handle it correctly.
- Produces one recipe set per valid combination of alternate choices

**Phase 2 — Quantity calculation (linear algebra)**
- Given a fixed recipe set from Phase 1, formulate a balance equation for every item: `production_rate − consumption_rate = net_output`
- Desired outputs fix their net output values; raw resource net outputs are unknowns (the inputs consumed from the budget)
- **If the recipe set is a DAG:** solve by arithmetic back-substitution from outputs to inputs. Fast and exact.
- **If the recipe set contains a cycle:** solve the full linear system with `numpy.linalg.solve`. Cycles become self-consistent constraints (e.g. the water recycled exactly satisfies part of the upstream water demand). The solution gives the net water input required.
- From the solution, compute per-recipe rates, then machine count and clock speed for each group (see Machine Counts section)
- Byproduct remainder: after byproducts satisfy declared in-chain demand, any remaining production of an undeclared item is an **implicit output**
- **Implicit outputs** — all items produced by the chain that were not declared as desired outputs are surfaced in the result with their rates. These are decision-relevant: a chain that produces a useful byproduct may be preferable to one that doesn't, even if both satisfy the declared outputs equally well.
- **Non-raw item deficits (Phase 1 retry):** after solving, Phase 2 checks every net-input item. Raw resource deficits are normal — they surface in the budget comparison. If a net-input item is *not* a raw resource, Phase 1 made a byproduct routing assumption that the quantities don't support (it skipped a dedicated recipe expecting the byproduct to cover demand, but the byproduct rate is insufficient). In this case, Phase 2 signals Phase 1 to retry that recipe set with the byproduct rule disabled for that specific item, forcing a dedicated recipe to be found. Each retry adds at most one recipe. A hard cap of **10 retries per recipe set** is enforced. If the cap is reached, the chain is discarded and the response includes an explicit error: *"A production chain for [output] could not be fully resolved after 10 attempts. The byproduct routing for [item] may involve an unusual cycle. Try adjusting your alternate recipe selections, or report this as a bug if you believe the inputs are valid."*
- **Degenerate cycles:** if `numpy.linalg.solve` raises `LinAlgError` (singular matrix — a perfectly self-sustaining cycle where a byproduct feeds back at exactly the rate consumed), the chain is discarded as degenerate and excluded from results. This is not expected to occur with real game data but is caught defensively.

**Post-solve**
- Compare total raw resource consumption per chain against the user's input budget; annotate with surplus/deficit per resource
- Chains that exceed the budget are included in results with a deficit warning and the exact per-resource delta — not filtered out
- The solver enforces an internal hard cap on the number of chains enumerated (default: 200, configurable) to prevent runaway computation on late-game items with many alternates. If the cap is hit, a warning is included in the response indicating results may be incomplete.
- All chains within the cap are retained and cached server-side. Results are never truncated before caching — truncation happens only at the display layer via pagination.
- Each result includes: full machine list, clock speeds, counts, declared outputs, implicit outputs with rates, and total resource consumption

**Failure reporting**
The solver must never return a silent empty result. Every no-result response includes a machine-readable reason and a human-readable explanation:
- *Phase 1 failure — no recipe path:* no sequence of recipes (given the user's unlocked alternates) can produce the desired output. Report which item in the dependency chain has no produceable recipe. The user's recourse is to unlock a different alternate.
- *Phase 2 failure — all chains have deficits:* recipe paths exist but every candidate requires at least one input the user did not declare. The summary card shows a generic message: "No viable chains found — all paths require undeclared inputs." Tapping the card expands a per-chain breakdown listing the specific missing inputs and rates for each candidate. The user's recourse is to declare the missing resources as inputs and re-solve.
- *Unknown item:* an item name in the request does not exist in the recipe graph. This is a data staleness problem — it occurs when a saved plan references an item added in a game version newer than the baked-in data file. The error message must say so explicitly: "Item '[name]' not found in recipe data. Your plan may reference items added in a newer game version — run `make fetch-game-data` and rebuild the image."
### API Endpoints (sketch)
- `GET /recipes` — full recipe list
- `GET /items` — full item list
- `POST /solve` — body: `{ inputs, outputs, unlocked_alternates, clocking_available }`; runs the solver, caches the full result set server-side, returns first page of results sorted by resource consumption (default), plus `solve_id`, `total_count`, `page`, `page_size`, and a `cap_reached` flag if the enumeration limit was hit
- `GET /solve/{solve_id}/results?sort=resource&page=1&page_size=10` — fetch any page of a cached result set with an arbitrary sort order, without re-running the solver. Sort values for Stage 1: `resource`. Stage 2 adds `power` and `build_cost`.
### Frontend (React)
Three-panel mobile layout:
1. **Inputs** — set available resources and rates
2. **Outputs** — set desired items and target rates
3. **Alternates** — toggle unlocked alternate recipes

**State management:** single `useReducer` at the top level managing the full app state — inputs, outputs, alternates, and solver result (idle / loading / success / error). All panels read from and dispatch to the same reducer. No external state library needed; the state shape is contained and colocated on one screen.

**Settings Panel:** Global toggle for enabling under/overclocking of machines. Other global settings that dictate solver behaviour such as optimizing for power consumption, build cost, etc. (see Stage 2) go here.

**Results view:** one card per valid chain. Cards are designed for quick visual comparison across chains, with deeper detail accessible on tap.

Each card shows:
- **Machine list** — recipe and count per machine group
- **Aggregate stat bars** — bars are scaled relative to the best result across all returned chains (shortest bar = most efficient), so ranking by eye is immediate. Stage 1 shows only the resource consumption bar. Power draw and build cost bars are added in Stage 2 when that data becomes available; they are not shown or placeholder-rendered in Stage 1.
- **Implicit outputs** — items produced but not declared as desired outputs, with rates
- **Deficit indicator** — if the chain exceeds the input budget, the resource bar overflows its track and a warning symbol (not solely colour) appears alongside it. The exact per-resource delta is shown in the detail table.

Tapping a card expands a **detail table** with one row per input resource: resource name, budget declared, amount consumed, and delta (surplus or deficit). This is the authoritative view for acting on a result.

Colour must not be the sole indicator of any state — the tool must be usable by colourblind users. Deficit vs. surplus is conveyed by bar overflow + symbol, not red vs. green.

**Sort and pagination controls** sit above the results list:
- Sort selector: toggles between available sort axes (Stage 1: resource consumption only; Stage 2 adds power and build cost). Changing sort order fetches the same `solve_id` with a new `sort` parameter — no re-solve.
- Results load in pages (default page size: 10). A "Load more" button appends the next page below the current results without replacing them, so previously reviewed cards remain visible.
- If `cap_reached` is true, a notice is shown above the results: "Result set may be incomplete — the solver reached its chain limit. Consider narrowing your alternate recipe selection."

**Footer / header:** game data version string (e.g. "Data: Steam Build 21237829") so the user can verify the recipe data matches their installed game version. The raw Steam build ID from `appmanifest_526870.acf` is used — no human-readable update name is available in the game files that have been investigated (`CustomVersions.json` contains internal Unreal Engine versions, not player-facing release names). During Commit 2, if a human-readable version string is discovered in `en-CA.json` or adjacent files, it should be preferred over the raw build ID.
## Planned Stages
### Stage 1 — Core Calculator
- Recipe data pipeline from Docs.json
- Solver: enumerate chains, compute machine counts/clocks
- Budget comparison and deficit warnings
- Mobile-friendly UI for the three inputs above
- Docker deployment
#### Commits

| #   | Commit                                                                                                                                                                                                                                                                                                              | Prereqs | Tests                                                                                                                                                                                             | Status             |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| 1   | **Dev environment** — `uv` project, Python pin, FastAPI + deps, Ruff + mypy + pytest-cov configured with coverage gate; Vite + React + Tailwind scaffold; Docker Compose skeleton; `Makefile` targets: `lint`, `typecheck`, `test`, `build`                                                                         | none    | `make lint && make typecheck && make test` pass on empty project                                                                                                                                  | done (`d015fe1`)   |
| 2   | **Docs.json parser** — typed Python models (`Item`, `Recipe`, `Machine`); parse `en-CA.json` (UTF-16); filter relevant `NativeClass` entries; extract item identifiers from Unreal class path strings; parse encoded `mIngredients`/`mProduct` strings; derive per-minute rates from per-cycle amounts and duration | 1       | Unit tests against a fixture subset of `en-CA.json`; assert correct per-minute rates; assert ingredient/product parsing for multi-input recipes; assert alternate recipes are flagged; mypy clean | done (`27ddb8e`)   |
| 3   | **Recipe graph + data endpoints** — build bipartite directed graph (item nodes + recipe nodes) from parsed models; wire `GET /items` and `GET /recipes`                                                                                                                                                             | 2       | Unit tests assert graph structure (node/edge count, known recipes present, cycles detectable e.g. aluminum); API integration tests via test client                                               | done (`f4f0dd1`)   |
| 4   | **Solver Phase 1: recipe selection** — DFS from desired output(s) back to raw resources, branching at every recipe choice; byproduct routing; cycle detection; produces one minimal recipe set per valid alternate combination                                                                                      | 3       | Unit tests on Modular Frame example assert correct recipe-set count per alternate combination; assert all leaf items are raw resources; assert aluminum chain flags a cycle; assert byproduct routing records in-chain dependency | done (`a61bee7`)   |
| 5   | **Solver Phase 2: quantity calculation** — for each recipe set from Phase 1: arithmetic back-substitution for acyclic sets; `numpy.linalg.solve` for cyclic sets; compute per-recipe rates, machine counts, clock speeds (with rounding and `clocking_available` flag), and implicit outputs                      | 4       | Unit tests assert quantities match spreadsheet for Modular Frame (acyclic); assert correct net water input for a cyclic aluminum fixture; clock rounding verified; `clocking_available=false` forces 100% | done (`30076e7`)   |
| 6   | **Budget checker** — sum resource consumption per chain, compare against available inputs, annotate with surplus/deficit                                                                                                                                                                                            | 5       | Unit tests for deficit case (Modular Frame −108 Iron Ingot) and surplus case                                                                                                                      | done (`55932f5`)   |
| 7   | **`POST /solve` + `GET /solve/{id}/results` endpoints** — run solver, cache results, return paginated first page with `solve_id`/`total_count`/`cap_reached`; results endpoint supports `sort` and `page` params; structured failure reasons for Phase 1 and Phase 2 failures                                    | 6       | Integration tests: valid request returns first page + metadata; second page fetch returns correct slice; sort param changes order; cap_reached flag set when limit hit; Phase 1 and Phase 2 failure responses | done (`7b2a5f8`)   |
| 8   | **React scaffold + API client** — Vite project structure, Tailwind config, typed fetch-based API client                                                                                                                                                                                                             | 1       | ESLint passes; Vitest smoke test for API client with mocked responses                                                                                                                             | done (`f058118`)   |
| 9   | **Input / Output / Alternates UI** — three-panel mobile layout, form state management                                                                                                                                                                                                                               | 8       | Vitest component tests: panel render, state updates, form validation                                                                                                                              | done (`1532ede`)   |
| 10  | **Results view** — chain result cards with resource bar, implicit outputs, deficit overflow indicator; tap-to-expand detail table; sort selector; "Load more" pagination (appends next page); `cap_reached` notice; Phase 1 and Phase 2 failure states                                                            | 7, 9    | Vitest: cards render with correct bar scaling; deficit card shows overflow + warning symbol; detail table renders correct rows; "Load more" appends without replacing; sort selector triggers correct API call; failure states render correct messages |                    |
| 11  | **Docker production build** — multi-stage frontend build, nginx config, Compose wiring, health checks                                                                                                                                                                                                               | 10      | `docker compose up` smoke test; `/health` returns 200; solve request returns results end-to-end                                                                                                   |                    |
### Stage 2 — Power and Build Cost
- Each machine has a power consumption rate in `en-CA.json`: `mPowerConsumption` (base MW) and `mPowerConsumptionExponent` (clock speed scaling factor, uniformly `1.321929` across all machines)
- Total power per chain becomes a second optimization axis
- Build cost (raw materials to construct the machines) as a third axis
- Results can be sorted/filtered by resource efficiency, power, or build cost
#### Commits

| # | Commit | Prereqs | Tests |
|---|---|---|---|
| 1 | **Extend models with power + build cost** — add power consumption and construction cost fields from `Docs.json` to `Recipe`/`Machine` models | Stage 1 complete | Unit tests assert fields present and correct on parsed models |
| 2 | **Solver: annotate chains with power and build cost totals** | Stage 2.1 | Unit tests assert correct totals on Modular Frame example |
| 3 | **API: expose power and build cost in solve response** | Stage 2.2 | Integration test asserts response shape and values |
| 4 | **Frontend: sort/filter results by resource, power, or build cost** | Stage 2.3 | Vitest tests for sort/filter logic; controls render and update results |
### Stage 3 — TBD
- Possibly: save/load factory plans
- Possibly: visual graph rendering of the production chain
- Possibly: shareable image exports of the visual graph rendering of a production chains
#### Commits
Not yet planned — scope depends on Stage 1 and 2 outcomes. Candidates:
- **Input discovery mode** — currently the user must declare available inputs before solving. In input discovery mode, the user declares only desired outputs; the solver computes the raw resources required and surfaces them as a shopping list. This lets the user identify a good map location before committing to a factory layout, without needing to pre-investigate the recipe space manually. Mechanically: the budget comparison step is skipped; instead, the raw resource requirements from Phase 2 are returned directly as the primary result, grouped by resource type and rate. Note: Stage 1's "all-chains-deficit" failure message already gives a partial version of this (it lists what's missing when all chains fail) — input discovery mode is the proactive, first-class version of that same information, surfaced as the intended result rather than as an error.
- Save/load factory plans (local storage or backend persistence)
- Visual graph rendering of a production chain. The renderer must handle disconnected subgraphs gracefully — a result that produces two unrelated items with no shared intermediates should render as two side-by-side sub-diagrams within the same card, not error or collapse into one.
- Shareable image export of the graph
## Session Notes
- Started: 2026-03-26
- Reference spreadsheet: `./Modular Frame.xlsx`
- Wiki: https://satisfactory.fandom.com/wiki/Satisfactory_Wiki

## Review Notes (2026-04-03)

Critiques identified before implementation. Resolved decisions logged inline below.

### Critical
1. **No-shared-intermediates error** — The spec says to return an error when two desired outputs share no intermediates. This prohibits valid multi-factory use cases and contradicts the 'surface options, don't make decisions' principle. **Resolved:** Error removed. Independent sub-chains are returned as a combined result. Maximum 10 requested outputs enforced as a UX cap. Stage 3 diagram renderer must handle disconnected subgraphs explicitly.
2. **Phase 1/Phase 2 retry convergence** — The claim 'converges in a small number of passes' is asserted without justification. No maximum retry count or failure mode if convergence doesn't occur. **Resolved:** Hard cap of 10 retries per recipe set. If exceeded, the chain is discarded with an explicit error message naming the problematic item and directing the user to adjust alternates or report a bug.
3. **Stage 1 UI shows Stage 2 bars** — Results cards include power draw and build cost bars, but that data doesn't exist until Stage 2. Behavior of those bars in Stage 1 is undefined. **Resolved:** Power and build cost bars are hidden entirely in Stage 1. They are added in Stage 2 when the data exists.
4. **`clocking_available=false` behavior in Phase 2** — Forcing 100% clock speed invalidates the continuous balance equations. How Phase 2 handles this mode (rounding, surplus, machine count selection) is not specified. **Resolved:** Phase 2 runs identically; clock speed is reported as 100% rather than the computed fraction. Surplus output is expected and surfaced in results.
5. **'All chains have deficits' failure reporting** — Aggregating missing inputs across all failed chains with a union is misleading (implies every chain needs all listed inputs, which is false). **Resolved:** Summary card shows a generic failure message. Tapping expands a per-chain breakdown of missing inputs, consistent with the existing detail table pattern.

### Significant Gaps
6. **Version string format inconsistency** — Architecture section shows raw Steam build ID; Frontend section shows 'Update 8.3'. These are different things; no mapping source is specified. **Resolved:** Raw Steam build ID used throughout. Implementation note added to check for a human-readable string in `en-CA.json` during Commit 2 and prefer it if found.
7. **Server-side result cache unspecified** — No TTL, eviction policy, maximum size, or restart behavior defined. **Resolved:** In-memory dict for Stage 1. No TTL, no eviction; cache is lost on server restart. Revisit in Stage 2 if needed.
8. **`solve_id` format unspecified** — UUID, sequential int, or hash of inputs? **Resolved:** UUID4.
9. **`GET /items` and `GET /recipes` underspecified** — No pagination, no spec of what the frontend does with this data or what shape it needs. Unresolved.
10. **DFS cap mid-traversal behavior** — When the 200-chain cap is hit during DFS, the behavior (abort branch, finish branch, drain stack) is unspecified. **Resolved:** Abort current branch immediately, mark `cap_reached=true`. No partial chains — results must always be fully usable.
11. **Alternates panel UX** — Should all alternates be shown, or only those relevant to selected outputs? No sort order specified. **Resolved:** Show only alternates relevant to the selected outputs, sorted alphabetically. Reduces clutter as the alternate list is large.
12. **Playwright CI bootstrapping** — Baselines don't exist at project start. First `make ci` run behavior is undefined. **Resolved:** `updateSnapshots: "missing"` — baselines are auto-generated on first run (test always passes); subsequent runs compare against committed baselines. Regenerate with `playwright update-snapshots` after intentional UI changes.
13. **CORS/nginx proxy config** — Vite proxies `/api` in dev, but production nginx proxy config is not specified. Unresolved.

### Minor
14. **Clock speed rounding assumption** — Spec assumes Satisfactory only allows whole-number clock speed increments. This may not be accurate in recent game versions. Unresolved.
15. **Build-gun recipe handling in Commit 2** — Should the Stage 1 parser store or discard build-gun recipes? **Resolved:** Parse and store in a separate collection, distinct from production recipes. Stage 2 needs them for build cost; Stage 1 ignores them at solve time.
16. **Auth/security** — No stated decision on whether the media server deployment is auth-gated or LAN-only. Unresolved.
