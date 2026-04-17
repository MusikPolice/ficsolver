"""Phase 1 solver: recipe selection via DFS.

Traverses the recipe dependency graph from desired output(s) back to raw
resources, branching at every item where multiple recipes are available.
Produces one minimal RecipeSelection per valid alternate combination.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from ficsolver.models import GameData, Recipe


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


def select_recipes(
    desired_outputs: list[str],
    unlocked_alternates: set[str],
    game_data: GameData,
    chain_limit: int = 200,
) -> Phase1Result:
    """Run Phase 1: enumerate minimal recipe sets via DFS.

    Returns one RecipeSelection per valid recipe combination up to chain_limit.
    When no selections are found, returns a Phase1Result with failure set.
    """
    selections: list[RecipeSelection] = []
    cap_reached = False

    for raw_selected, byproduct_deps in _dfs(
        list(desired_outputs),
        {},
        {},
        set(),
        unlocked_alternates,
        game_data,
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
        )
        return

    producers = _get_available_producers(item_class, game_data, unlocked_alternates)

    if not producers:
        if _has_any_producer(item_class, game_data):
            # Has recipes but none are unlocked — branch is blocked; don't yield.
            return
        # Raw resource (no recipe exists at all) — treat as a given input.
        yield from _dfs(
            rest, selected, byproduct_deps, new_processed, unlocked_alternates, game_data
        )
        return

    # Branch: one path per available producer recipe.
    for recipe in producers:
        if recipe.class_name in selected:
            # Already selected via another path; don't re-add.
            yield from _dfs(
                rest, selected, byproduct_deps, new_processed, unlocked_alternates, game_data
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
) -> list[Recipe]:
    """Return standard recipes + unlocked alternates that produce item_class."""
    return [
        r
        for r in game_data.recipes
        if not r.is_build_gun
        and any(p.item_class == item_class for p in r.products)
        and (not r.is_alternate or r.class_name in unlocked_alternates)
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
