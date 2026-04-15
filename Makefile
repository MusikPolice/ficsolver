.PHONY: lint typecheck test test-visual build ci verify fetch-game-data

# ---------------------------------------------------------------------------
# Game data — must be run before `make build` when the game updates
# Usage: make fetch-game-data GAME_DIR=/path/to/game
# ---------------------------------------------------------------------------
fetch-game-data:
	@if [ -z "$(GAME_DIR)" ]; then \
		echo "Error: GAME_DIR is required. Usage: make fetch-game-data GAME_DIR=/path/to/game"; \
		exit 1; \
	fi
	mkdir -p data/game
	cp "$(GAME_DIR)/CommunityResources/Docs/en-CA.json" data/game/
	@ACF="$(GAME_DIR)/../../appmanifest_526870.acf"; \
	BUILD_ID=$$(grep '"buildid"' "$$ACF" | sed 's/.*"\([0-9]*\)".*/\1/'); \
	printf '{"steam_build_id":"%s"}\n' "$$BUILD_ID" > data/game/version.json; \
	echo "Fetched game data (Steam build $$BUILD_ID)"

# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------
lint:
	cd backend && uv run ruff check .
	cd backend && uv run ruff format --check .
	cd frontend && pnpm lint

# ---------------------------------------------------------------------------
# Type check
# ---------------------------------------------------------------------------
typecheck:
	cd backend && uv run mypy src/
	cd frontend && pnpm typecheck

# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------
test:
	cd backend && uv run pytest
	cd frontend && pnpm test

# ---------------------------------------------------------------------------
# Visual regression tests (Playwright)
# ---------------------------------------------------------------------------
test-visual:
	cd frontend && pnpm test:visual

# ---------------------------------------------------------------------------
# Production build
# ---------------------------------------------------------------------------
build:
	@if [ ! -f data/game/en-CA.json ]; then \
		echo "Error: data/game/en-CA.json not found. Run 'make fetch-game-data GAME_DIR=...' first."; \
		exit 1; \
	fi
	docker compose build

# ---------------------------------------------------------------------------
# Pre-commit / local verification (lint + typecheck + unit tests)
# ---------------------------------------------------------------------------
verify: lint typecheck test

# ---------------------------------------------------------------------------
# CI pipeline (ordered)
# ---------------------------------------------------------------------------
ci: lint typecheck test test-visual build
