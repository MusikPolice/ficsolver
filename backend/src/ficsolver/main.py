import os
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from ficsolver.models import BudgetComparison, GameData, Item, Recipe, SolverChain
from ficsolver.parser import load_game_data
from ficsolver.solver import (
    RecipeSelection,
    calculate_quantities,
    check_budget,
    retry_with_dedicated_recipe,
    select_recipes,
)

app = FastAPI(title="ficsolver")

_GAME_DATA_PATH = Path(os.getenv("GAME_DATA_PATH", "/data/game/en-CA.json"))
_MAX_RETRIES = 10
_DEFAULT_PAGE_SIZE = 10


@lru_cache(maxsize=1)
def get_game_data() -> GameData:
    return load_game_data(_GAME_DATA_PATH)


GameDataDep = Annotated[GameData, Depends(get_game_data)]


# ---------------------------------------------------------------------------
# API request / response models
# ---------------------------------------------------------------------------


class SolveRequest(BaseModel):
    inputs: dict[str, float] = Field(default_factory=dict)
    outputs: dict[str, float]
    unlocked_alternates: list[str] = Field(default_factory=list)
    clocking_available: bool = True
    page_size: int = Field(default=_DEFAULT_PAGE_SIZE, ge=1, le=100)

    @model_validator(mode="after")
    def validate_outputs_count(self) -> "SolveRequest":
        if not self.outputs:
            raise ValueError("outputs must contain at least one item")
        if len(self.outputs) > 10:
            raise ValueError("outputs may contain at most 10 items")
        return self


class MachineGroupOut(BaseModel):
    recipe_class: str
    recipe_display_name: str
    machine_class: str
    machine_count: int
    clock_speed_pct: int
    exact_recipe_rate: float


class BudgetEntryOut(BaseModel):
    item_class: str
    available: float
    consumed: float
    delta: float


class ChainResultOut(BaseModel):
    machine_groups: list[MachineGroupOut]
    raw_resource_consumption: dict[str, float]
    implicit_outputs: dict[str, float]
    has_cycle: bool
    budget: dict[str, BudgetEntryOut]
    has_deficit: bool
    total_resource_consumed: float


class SolveFailureOut(BaseModel):
    failure_type: Literal["phase1", "phase2"]
    message: str
    item_class: str | None = None
    chain_deficits: list[dict[str, float]] | None = None


class SolveResponse(BaseModel):
    solve_id: str | None = None
    total_count: int
    page: int
    page_size: int
    cap_reached: bool
    results: list[ChainResultOut]
    failure: SolveFailureOut | None = None
    all_chains_have_deficit: bool = False
    warnings: list[str] | None = None


# ---------------------------------------------------------------------------
# In-memory result cache
# ---------------------------------------------------------------------------


@dataclass
class _CachedSolve:
    chains: list[ChainResultOut]
    cap_reached: bool


_solve_cache: dict[str, _CachedSolve] = {}


# ---------------------------------------------------------------------------
# Solver orchestration helpers
# ---------------------------------------------------------------------------


def _chain_to_out(chain: SolverChain, budget: BudgetComparison) -> ChainResultOut:
    machine_groups = [
        MachineGroupOut(
            recipe_class=mg.recipe.class_name,
            recipe_display_name=mg.recipe.display_name,
            machine_class=mg.recipe.machine_class,
            machine_count=mg.machine_count,
            clock_speed_pct=mg.clock_speed_pct,
            exact_recipe_rate=mg.exact_recipe_rate,
        )
        for mg in chain.machine_groups
    ]
    budget_out = {
        item_class: BudgetEntryOut(
            item_class=entry.item_class,
            available=entry.available,
            consumed=entry.consumed,
            delta=entry.delta,
        )
        for item_class, entry in budget.entries.items()
    }
    return ChainResultOut(
        machine_groups=machine_groups,
        raw_resource_consumption=chain.raw_resource_consumption,
        implicit_outputs=chain.implicit_outputs,
        has_cycle=chain.has_cycle,
        budget=budget_out,
        has_deficit=budget.has_deficit,
        total_resource_consumed=sum(chain.raw_resource_consumption.values()),
    )


def _solve_selection(
    selection: RecipeSelection,
    desired_outputs: dict[str, float],
    available_inputs: dict[str, float],
    clocking_available: bool,
    game_data: GameData,
    unlocked_alternates: set[str],
) -> ChainResultOut | str | None:
    """Run Phase 2 with retry logic for one RecipeSelection.

    Returns ChainResultOut on success, an error string if the retry cap is hit,
    or None if the selection cannot be solved and should be silently discarded.
    """
    current = selection
    for attempt in range(_MAX_RETRIES + 1):
        result = calculate_quantities(current, desired_outputs, clocking_available, game_data)
        if isinstance(result, SolverChain):
            budget = check_budget(result, available_inputs)
            return _chain_to_out(result, budget)

        # Phase2Failure — try to add a dedicated recipe for the failing item.
        if attempt == _MAX_RETRIES:
            output_names = ", ".join(
                game_data.items[ic].display_name if ic in game_data.items else ic
                for ic in desired_outputs
            )
            item_obj = game_data.items.get(result.item_class)
            item_name = item_obj.display_name if item_obj else result.item_class
            return (
                f"A production chain for {output_names} could not be fully resolved after "
                f"{_MAX_RETRIES} attempts. The byproduct routing for '{item_name}' may involve "
                "an unusual cycle. Try adjusting your alternate recipe selections, or report "
                "this as a bug if you believe the inputs are valid."
            )

        augmented = retry_with_dedicated_recipe(
            current, result.item_class, game_data, unlocked_alternates
        )
        if augmented is None:
            return None  # No producer available; discard silently.
        current = augmented

    return None  # Unreachable; satisfies mypy.


def _sort_chains(chains: list[ChainResultOut], sort: str) -> list[ChainResultOut]:
    if sort == "resource":
        return sorted(chains, key=lambda c: c.total_resource_consumed)
    return list(chains)


# ---------------------------------------------------------------------------
# Existing endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/items")
def list_items(game_data: GameDataDep) -> list[Item]:
    return sorted(
        (item for item in game_data.items.values() if item.display_name),
        key=lambda i: i.display_name,
    )


@app.get("/recipes")
def list_recipes(game_data: GameDataDep) -> list[Recipe]:
    return game_data.recipes


# ---------------------------------------------------------------------------
# Solve endpoints
# ---------------------------------------------------------------------------


@app.post("/solve")
def solve(request: SolveRequest, game_data: GameDataDep) -> SolveResponse:
    # Validate that all requested item classes exist in game data.
    all_requested = list(request.outputs) + list(request.inputs)
    unknown = [ic for ic in all_requested if ic not in game_data.items]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Item(s) {unknown!r} not found in recipe data. Your plan may reference items "
                "added in a newer game version — run `make fetch-game-data` and rebuild the image."
            ),
        )

    desired_outputs = request.outputs
    available_inputs = request.inputs
    unlocked_alternates = set(request.unlocked_alternates)

    # Phase 1: enumerate recipe selections.
    phase1_result = select_recipes(
        list(desired_outputs.keys()),
        unlocked_alternates,
        game_data,
        available_inputs=set(available_inputs.keys()),
    )

    if phase1_result.failure is not None:
        return SolveResponse(
            total_count=0,
            page=1,
            page_size=request.page_size,
            cap_reached=False,
            results=[],
            failure=SolveFailureOut(
                failure_type="phase1",
                message=phase1_result.failure.message,
                item_class=phase1_result.failure.item_class,
            ),
        )

    # Phase 2: solve each selection with retry, then run budget check.
    chain_results: list[ChainResultOut] = []
    warnings: list[str] = []

    for selection in phase1_result.selections:
        outcome = _solve_selection(
            selection,
            desired_outputs,
            available_inputs,
            request.clocking_available,
            game_data,
            unlocked_alternates,
        )
        if isinstance(outcome, str):
            warnings.append(outcome)
        elif outcome is not None:
            chain_results.append(outcome)

    if not chain_results:
        return SolveResponse(
            total_count=0,
            page=1,
            page_size=request.page_size,
            cap_reached=phase1_result.cap_reached,
            results=[],
            failure=SolveFailureOut(
                failure_type="phase2",
                message="No viable chains found — all paths could not be fully resolved.",
            ),
            warnings=warnings if warnings else None,
        )

    # Sort by total resource consumption (ascending) then cache.
    sorted_chains = _sort_chains(chain_results, "resource")
    all_have_deficit = all(c.has_deficit for c in sorted_chains)

    solve_id = str(uuid.uuid4())
    _solve_cache[solve_id] = _CachedSolve(
        chains=sorted_chains, cap_reached=phase1_result.cap_reached
    )

    first_page = sorted_chains[: request.page_size]

    return SolveResponse(
        solve_id=solve_id,
        total_count=len(sorted_chains),
        page=1,
        page_size=request.page_size,
        cap_reached=phase1_result.cap_reached,
        results=first_page,
        all_chains_have_deficit=all_have_deficit,
        warnings=warnings if warnings else None,
    )


@app.get("/solve/{solve_id}/results")
def get_solve_results(
    solve_id: str,
    sort: str = "resource",
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
) -> SolveResponse:
    cached = _solve_cache.get(solve_id)
    if cached is None:
        raise HTTPException(status_code=404, detail=f"Solve ID '{solve_id}' not found.")

    sorted_chains = _sort_chains(cached.chains, sort)
    total = len(sorted_chains)
    start = (page - 1) * page_size
    end = start + page_size
    page_results = sorted_chains[start:end]

    return SolveResponse(
        solve_id=solve_id,
        total_count=total,
        page=page,
        page_size=page_size,
        cap_reached=cached.cap_reached,
        results=page_results,
        all_chains_have_deficit=all(c.has_deficit for c in sorted_chains),
    )
