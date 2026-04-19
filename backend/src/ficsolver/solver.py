"""Solver: Phase 1 (recipe selection via DFS) and Phase 2 (quantity calculation).

Phase 1 traverses the recipe dependency graph from desired output(s) back to raw
resources, branching at every item where multiple recipes are available.
Produces one minimal RecipeSelection per valid alternate combination.

Phase 2 takes each RecipeSelection and solves for per-recipe rates using
arithmetic back-substitution (acyclic chains) or numpy.linalg.lstsq (cyclic
chains).  It then derives machine counts and clock speeds from those rates.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from dataclasses import dataclass, field

import numpy as np

from ficsolver.models import (
    BudgetComparison,
    GameData,
    MachineGroup,
    Recipe,
    ResourceBudgetEntry,
    SolverChain,
)


@dataclass
class RecipeSelection:
    """One candidate recipe set produced by Phase 1."""

    recipes: dict[str, Recipe]
    has_cycle: bool
    byproduct_deps: dict[str, str] = field(default_factory=dict)
    """Maps item_class → recipe_class_name that covers it via byproduct routing."""


@dataclass
class Phase1Failure:
    """Describes why Phase 1 found no valid chains."""

    item_class: str
    message: str


@dataclass
class Phase1Result:
    """Output of select_recipes."""

    selections: list[RecipeSelection]
    cap_reached: bool
    failure: Phase1Failure | None = None


_CONVERTER_MACHINE_CLASS = "Build_Converter_C"


def select_recipes(
    desired_outputs: list[str],
    unlocked_alternates: set[str],
    game_data: GameData,
    chain_limit: int = 200,
    available_inputs: set[str] | None = None,
    exclude_converter_recipes: bool = False,
) -> Phase1Result:
    """Run Phase 1: enumerate minimal recipe sets via DFS.

    Returns one RecipeSelection per valid recipe combination up to chain_limit.
    When no selections are found, returns a Phase1Result with failure set.

    available_inputs: item classes the user has declared as on-hand.  Items in
    this set are treated like raw resources in the DFS — the solver will offer
    a branch where they are taken as given rather than produced via recipe.

    exclude_converter_recipes: when True, recipes that run in the Converter
    building (SAM-based resource conversion) are excluded from all branches.
    """
    declared: set[str] = available_inputs or set()
    selections: list[RecipeSelection] = []
    cap_reached = False

    for raw_selected, byproduct_deps in _dfs(
        list(desired_outputs),
        {},
        {},
        set(),
        unlocked_alternates,
        game_data,
        declared,
        exclude_converter_recipes,
    ):
        has_cycle = _detect_cycle(raw_selected)
        selections.append(RecipeSelection(raw_selected, has_cycle, byproduct_deps))
        if len(selections) >= chain_limit:
            cap_reached = True
            break

    if not selections:
        failure = _find_failure(desired_outputs, game_data, unlocked_alternates)
        return Phase1Result([], False, failure)

    return Phase1Result(selections, cap_reached)


# ---------------------------------------------------------------------------
# DFS
# ---------------------------------------------------------------------------


def _dfs(
    items_queue: list[str],
    selected: dict[str, Recipe],
    byproduct_deps: dict[str, str],
    processed: set[str],
    unlocked_alternates: set[str],
    game_data: GameData,
    available_inputs: set[str],
    exclude_converter_recipes: bool = False,
) -> Iterator[tuple[dict[str, Recipe], dict[str, str]]]:
    """Yield (selected_recipes, byproduct_deps) for each fully-resolved chain."""

    # Skip items already handled in this branch.
    while items_queue and items_queue[0] in processed:
        items_queue = items_queue[1:]

    if not items_queue:
        yield dict(selected), dict(byproduct_deps)
        return

    item_class = items_queue[0]
    rest = list(items_queue[1:])
    new_processed = processed | {item_class}

    # Byproduct routing: item already produced by a selected recipe?
    covering = _find_byproduct_producer(item_class, selected)
    if covering is not None:
        yield from _dfs(
            rest,
            selected,
            {**byproduct_deps, item_class: covering},
            new_processed,
            unlocked_alternates,
            game_data,
            available_inputs,
            exclude_converter_recipes,
        )
        return

    producers = _get_available_producers(
        item_class, game_data, unlocked_alternates, exclude_converter_recipes
    )

    # Determine whether this item can be treated as a terminal input rather than
    # always being produced via a recipe.  This is true when the item is a
    # naturally-occurring raw resource (e.g. Iron Ore — mineable even though
    # Converter recipes also exist for it) or when the user has declared it as
    # an available input.
    item_obj = game_data.items.get(item_class)
    is_obtainable_as_input = item_class in available_inputs or (
        item_obj is not None and item_obj.is_raw_resource
    )

    if not producers:
        if _has_any_producer(item_class, game_data) and not is_obtainable_as_input:
            # Has recipes but none are unlocked and it isn't a raw/declared
            # resource — this branch is blocked; don't yield.
            return
        # No available producers, or it's a raw/declared resource regardless:
        # treat as a given input and continue resolving the rest of the chain.
        yield from _dfs(
            rest,
            selected,
            byproduct_deps,
            new_processed,
            unlocked_alternates,
            game_data,
            available_inputs,
            exclude_converter_recipes,
        )
        return

    # For raw resources and declared inputs that also have producer recipes
    # (e.g. Iron Ore has Converter recipes), offer a branch where the item is
    # simply mined / taken from stock rather than produced via recipe.
    if is_obtainable_as_input:
        yield from _dfs(
            rest,
            selected,
            byproduct_deps,
            new_processed,
            unlocked_alternates,
            game_data,
            available_inputs,
            exclude_converter_recipes,
        )

    # For explicitly declared available inputs, don't explore producer recipe
    # branches — producing something the user already has is strictly worse.
    # Raw resources (not declared) may still branch into Converter recipes.
    if item_class in available_inputs:
        return

    # Branch: one path per available producer recipe.
    for recipe in producers:
        if recipe.class_name in selected:
            # Already selected via another path; don't re-add.
            yield from _dfs(
                rest,
                selected,
                byproduct_deps,
                new_processed,
                unlocked_alternates,
                game_data,
                available_inputs,
                exclude_converter_recipes,
            )
            continue

        new_selected = {**selected, recipe.class_name: recipe}
        new_ingredients = [
            ing.item_class for ing in recipe.ingredients if ing.item_class not in new_processed
        ]
        yield from _dfs(
            new_ingredients + rest,
            new_selected,
            byproduct_deps,
            new_processed,
            unlocked_alternates,
            game_data,
            available_inputs,
            exclude_converter_recipes,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_byproduct_producer(item_class: str, selected: dict[str, Recipe]) -> str | None:
    """Return the class_name of a selected recipe that produces item_class, or None."""
    for recipe_class, recipe in selected.items():
        if any(p.item_class == item_class for p in recipe.products):
            return recipe_class
    return None


def _get_available_producers(
    item_class: str,
    game_data: GameData,
    unlocked_alternates: set[str],
    exclude_converter_recipes: bool = False,
) -> list[Recipe]:
    """Return standard recipes + unlocked alternates that produce item_class."""
    return [
        r
        for r in game_data.recipes
        if not r.is_build_gun
        and any(p.item_class == item_class for p in r.products)
        and (not r.is_alternate or r.class_name in unlocked_alternates)
        and not (exclude_converter_recipes and r.machine_class == _CONVERTER_MACHINE_CLASS)
    ]


def _has_any_producer(item_class: str, game_data: GameData) -> bool:
    """Return True if any production recipe (including locked alternates) produces item_class."""
    return any(
        not r.is_build_gun and any(p.item_class == item_class for p in r.products)
        for r in game_data.recipes
    )


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------


def _detect_cycle(selected: dict[str, Recipe]) -> bool:
    """Return True if the selected recipe set has a cyclic inter-recipe dependency.

    A dependency edge exists from recipe R2 to recipe R1 when R1 produces
    something that R2 needs.  A cycle in this directed graph means Phase 2
    must use numpy.linalg.solve instead of back-substitution.
    """
    # Build: recipe_class → set of recipe_classes it depends on.
    deps: dict[str, set[str]] = {rcn: set() for rcn in selected}

    for rcn, recipe in selected.items():
        for ing in recipe.ingredients:
            provider = _find_byproduct_producer(ing.item_class, selected)
            if provider is None:
                continue
            if provider == rcn:
                # Self-dependency — immediate cycle.
                return True
            deps[rcn].add(provider)

    # DFS cycle detection.
    UNVISITED, IN_PROGRESS, DONE = 0, 1, 2
    state: dict[str, int] = {rcn: UNVISITED for rcn in selected}

    def _visit(node: str) -> bool:
        state[node] = IN_PROGRESS
        for dep in deps[node]:
            if state[dep] == IN_PROGRESS:
                return True
            if state[dep] == UNVISITED and _visit(dep):
                return True
        state[node] = DONE
        return False

    return any(_visit(n) for n in selected if state[n] == UNVISITED)


# ---------------------------------------------------------------------------
# Failure detection
# ---------------------------------------------------------------------------


def _find_failure(
    desired_outputs: list[str],
    game_data: GameData,
    unlocked_alternates: set[str],
) -> Phase1Failure:
    """BFS to find the first item that blocks all recipe paths."""
    queue = list(desired_outputs)
    visited: set[str] = set()

    while queue:
        item_class = queue.pop(0)
        if item_class in visited:
            continue
        visited.add(item_class)

        available = _get_available_producers(item_class, game_data, unlocked_alternates)
        has_any = _has_any_producer(item_class, game_data)

        if has_any and not available:
            item_obj = game_data.items.get(item_class)
            name = item_obj.display_name if item_obj else item_class
            return Phase1Failure(
                item_class=item_class,
                message=(
                    f"No recipe available for '{name}'. Unlock a recipe that produces this item."
                ),
            )

        for recipe in available:
            for ing in recipe.ingredients:
                if ing.item_class not in visited:
                    queue.append(ing.item_class)

    item_class = desired_outputs[0] if desired_outputs else ""
    item_obj = game_data.items.get(item_class)
    name = item_obj.display_name if item_obj else item_class
    return Phase1Failure(
        item_class=item_class,
        message=f"No valid recipe chains found for '{name}'.",
    )


# ===========================================================================
# Phase 2: quantity calculation
# ===========================================================================


@dataclass
class Phase2Failure:
    """A non-raw item has a net deficit — Phase 1 byproduct routing was insufficient."""

    item_class: str
    message: str


def calculate_quantities(
    selection: RecipeSelection,
    desired_outputs: dict[str, float],
    clocking_available: bool,
    game_data: GameData,
) -> SolverChain | Phase2Failure:
    """Run Phase 2: solve for recipe rates and derive machine groups.

    For acyclic recipe sets uses arithmetic back-substitution; for cyclic sets
    uses numpy.linalg.lstsq.  Returns Phase2Failure when a non-raw item ends
    up with a net deficit (byproduct routing assumption was wrong).
    """
    recipes = list(selection.recipes.values())
    if not recipes:
        return SolverChain([], {}, {}, False)

    produced_items: set[str] = {p.item_class for r in recipes for p in r.products}
    all_items: set[str] = produced_items | {i.item_class for r in recipes for i in r.ingredients}
    raw_resources = all_items - produced_items
    non_raw_items = sorted(all_items - raw_resources)

    # Items whose demand must NOT drive the producing recipe's rate — Phase 1
    # assumes the byproduct-producing recipe is already running at the rate needed
    # for its primary products and will produce these items as a side effect.
    byproduct_items: set[str] = set(selection.byproduct_deps.keys())

    solve_result: dict[str, float] | Phase2Failure
    if selection.has_cycle:
        solve_result = _solve_with_numpy(recipes, desired_outputs, non_raw_items)
    else:
        solve_result = _back_substitution(recipes, desired_outputs, raw_resources, byproduct_items)

    if isinstance(solve_result, Phase2Failure):
        return solve_result

    recipe_rates = solve_result

    # Check for non-raw deficits (Phase 1 byproduct routing assumption violated).
    for item_class in non_raw_items:
        if item_class in desired_outputs:
            continue
        net = _compute_net(item_class, recipe_rates, recipes)
        if net < -1e-6:
            item_obj = game_data.items.get(item_class)
            name = item_obj.display_name if item_obj else item_class
            return Phase2Failure(
                item_class=item_class,
                message=(
                    f"Byproduct routing for '{name}' is insufficient. "
                    "Phase 1 must retry with a dedicated recipe for this item."
                ),
            )

    machine_groups: list[MachineGroup] = []
    for recipe in recipes:
        rate = recipe_rates.get(recipe.class_name, 0.0)
        count = math.ceil(rate) if rate > 1e-9 else 1
        if clocking_available:
            clock_pct = math.ceil(rate / count * 100) if count > 0 else 100
        else:
            clock_pct = 100
        machine_groups.append(
            MachineGroup(
                recipe=recipe,
                machine_count=count,
                clock_speed_pct=clock_pct,
                exact_recipe_rate=rate,
            )
        )

    raw_consumption: dict[str, float] = {}
    for raw_item in raw_resources:
        total = sum(
            recipe_rates.get(r.class_name, 0.0) * ing.amount_per_min
            for r in recipes
            for ing in r.ingredients
            if ing.item_class == raw_item
        )
        if total > 1e-9:
            raw_consumption[raw_item] = total

    implicit_outputs: dict[str, float] = {}
    for item_class in non_raw_items:
        if item_class in desired_outputs:
            continue
        net = _compute_net(item_class, recipe_rates, recipes)
        if net > 1e-9:
            implicit_outputs[item_class] = net

    return SolverChain(
        machine_groups=machine_groups,
        raw_resource_consumption=raw_consumption,
        implicit_outputs=implicit_outputs,
        has_cycle=selection.has_cycle,
    )


# ---------------------------------------------------------------------------
# Phase 2 helpers
# ---------------------------------------------------------------------------


def _compute_net(item_class: str, recipe_rates: dict[str, float], recipes: list[Recipe]) -> float:
    """Net production of item_class at the given recipe rates (positive = surplus)."""
    net = 0.0
    for recipe in recipes:
        rate = recipe_rates.get(recipe.class_name, 0.0)
        for p in recipe.products:
            if p.item_class == item_class:
                net += rate * p.amount_per_min
        for ing in recipe.ingredients:
            if ing.item_class == item_class:
                net -= rate * ing.amount_per_min
    return net


def _back_substitution(
    recipes: list[Recipe],
    desired_outputs: dict[str, float],
    raw_resources: set[str],
    byproduct_items: set[str],
) -> dict[str, float] | Phase2Failure:
    """Solve recipe rates by back-substitution for acyclic recipe sets.

    Performs a topological traversal from desired outputs to raw resources,
    computing each recipe's rate from the accumulated demand for its products.

    byproduct_items: items whose demand must not drive the producing recipe's rate —
    Phase 1 assumed they are covered as byproducts at whatever rate the recipe
    already runs for its primary products.  After solving, the caller checks
    whether those byproduct rates are sufficient.
    """
    # Build: item_class -> recipe that produces it (unique per item in a DAG).
    producer_map: dict[str, Recipe] = {}
    for recipe in recipes:
        for p in recipe.products:
            if p.item_class not in raw_resources:
                producer_map[p.item_class] = recipe

    # Topological sort of recipes so dependencies come before dependents.
    topo_order = _topological_sort(recipes, producer_map)

    # Accumulate demand for each item, then process recipes in reverse topo order
    # (desired-output recipes first, raw-resource-facing recipes last).
    item_demand: dict[str, float] = dict(desired_outputs)
    recipe_rates: dict[str, float] = {}

    for recipe in reversed(topo_order):
        # Determine rate: maximum across non-byproduct products that have demand.
        # Byproduct items are excluded — their demand must not inflate the recipe
        # rate; the post-solve deficit check will catch any shortfall.
        rate = 0.0
        for p in recipe.products:
            if p.item_class in byproduct_items:
                continue
            demand = item_demand.get(p.item_class, 0.0)
            if demand > 1e-12 and p.item_class not in raw_resources:
                rate = max(rate, demand / p.amount_per_min)

        if rate < 1e-12:
            continue

        recipe_rates[recipe.class_name] = rate

        for ing in recipe.ingredients:
            if ing.item_class not in raw_resources:
                item_demand[ing.item_class] = (
                    item_demand.get(ing.item_class, 0.0) + rate * ing.amount_per_min
                )

    return recipe_rates


def _topological_sort(recipes: list[Recipe], producer_map: dict[str, Recipe]) -> list[Recipe]:
    """Return recipes in topological order (dependencies before dependents)."""
    recipe_map = {r.class_name: r for r in recipes}

    # Dependency edges: recipe -> recipes whose products it consumes.
    deps: dict[str, set[str]] = {r.class_name: set() for r in recipes}
    for recipe in recipes:
        for ing in recipe.ingredients:
            if ing.item_class in producer_map:
                dep_rcn = producer_map[ing.item_class].class_name
                if dep_rcn != recipe.class_name:
                    deps[recipe.class_name].add(dep_rcn)

    order: list[str] = []
    perm: set[str] = set()
    temp: set[str] = set()

    def _visit(rcn: str) -> None:
        if rcn in perm:
            return
        temp.add(rcn)
        for dep in deps[rcn]:
            if dep not in perm:
                _visit(dep)
        temp.discard(rcn)
        perm.add(rcn)
        order.append(rcn)

    for rcn in recipe_map:
        if rcn not in perm:
            _visit(rcn)

    return [recipe_map[rcn] for rcn in order]


def _solve_with_numpy(
    recipes: list[Recipe],
    desired_outputs: dict[str, float],
    non_raw_items: list[str],
) -> dict[str, float] | Phase2Failure:
    """Solve recipe rates for cyclic recipe sets using numpy least squares.

    Sets up the balance-equation matrix A (rows = items, cols = recipes) and
    solves A·x = b where b holds target rates for desired outputs and 0 for
    intermediates.
    """
    n_items = len(non_raw_items)
    n_recipes = len(recipes)

    item_to_row = {item: i for i, item in enumerate(non_raw_items)}

    A = np.zeros((n_items, n_recipes))
    b = np.zeros(n_items)

    for j, recipe in enumerate(recipes):
        for p in recipe.products:
            if p.item_class in item_to_row:
                A[item_to_row[p.item_class], j] += p.amount_per_min
        for ing in recipe.ingredients:
            if ing.item_class in item_to_row:
                A[item_to_row[ing.item_class], j] -= ing.amount_per_min

    for item_class, rate in desired_outputs.items():
        if item_class in item_to_row:
            b[item_to_row[item_class]] = rate

    x: np.ndarray
    try:
        x, _residuals, _rank, _sv = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return Phase2Failure("", "Degenerate cycle in production chain — cannot solve.")

    # Verify the solution is self-consistent (degenerate cycles give large residuals).
    residual = float(np.max(np.abs(A @ x - b)))
    tolerance = 1e-6 * max(1.0, float(np.max(np.abs(b))))
    if residual > tolerance:
        return Phase2Failure(
            "", "Degenerate cycle in production chain — inconsistent balance equations."
        )

    # Reject solutions with negative recipe rates — these arise from degenerate
    # converter cycles (e.g. CopperOre → CateriumOre → Bauxite → RawQuartz →
    # CopperOre) where lstsq finds an infinite family of solutions and returns a
    # minimum-norm one that is physically meaningless.
    if any(float(xi) < -1e-6 for xi in x):
        return Phase2Failure(
            "", "Cyclic recipe chain produces negative rates — degenerate converter cycle."
        )

    return {recipe.class_name: float(x[j]) for j, recipe in enumerate(recipes)}


# ===========================================================================
# Budget checker
# ===========================================================================


def check_budget(
    chain: SolverChain,
    available_inputs: dict[str, float],
) -> BudgetComparison:
    """Compare chain resource consumption against the user's declared inputs.

    Returns one ResourceBudgetEntry per resource that is either consumed by the
    chain or declared as available (or both).  delta = available - consumed;
    negative means a deficit.
    """
    all_resources = set(chain.raw_resource_consumption) | set(available_inputs)
    entries: dict[str, ResourceBudgetEntry] = {}
    has_deficit = False

    for item_class in all_resources:
        available = available_inputs.get(item_class, 0.0)
        consumed = chain.raw_resource_consumption.get(item_class, 0.0)
        delta = available - consumed
        if delta < 0:
            has_deficit = True
        entries[item_class] = ResourceBudgetEntry(
            item_class=item_class,
            available=available,
            consumed=consumed,
            delta=delta,
        )

    return BudgetComparison(entries=entries, has_deficit=has_deficit)


# ===========================================================================
# Phase 2 retry support
# ===========================================================================


def retry_with_dedicated_recipe(
    selection: RecipeSelection,
    item_class: str,
    game_data: GameData,
    unlocked_alternates: set[str],
) -> RecipeSelection | None:
    """Return a new selection that adds a dedicated recipe for item_class.

    Used when Phase 2 returns Phase2Failure because a byproduct rate is
    insufficient.  Removes the byproduct dependency for item_class and adds
    the first available producer recipe that is not already in the selection.
    Returns None if no such producer exists.
    """
    producers = _get_available_producers(item_class, game_data, unlocked_alternates)
    for producer in producers:
        if producer.class_name not in selection.recipes:
            new_recipes = {**selection.recipes, producer.class_name: producer}
            new_deps = {k: v for k, v in selection.byproduct_deps.items() if k != item_class}
            return RecipeSelection(new_recipes, _detect_cycle(new_recipes), new_deps)
    return None
