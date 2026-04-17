"""Tests for solver Phase 1: DFS recipe selection.

Uses the Zorblax universe fixture.  Key recipe paths:

  ZorblaxFrame
    → ReinforcedZorblaxPlate (standard: Recipe_ReinforcedZorblaxPlate_C)
       OR Bonded alt (Recipe_Alternate_BondedZorblaxPlate_C, needs Sprongite)
    → ZorblaxRod

  ZorblaxGear — only via alternate Recipe_Alternate_ZorblaxGear_C
"""

import pytest

from ficsolver.models import GameData
from ficsolver.parser import parse_game_data
from ficsolver.solver import Phase1Failure, select_recipes
from tests.fixtures.game_data import CYCLIC_FIXTURE, FIXTURE

FRAME = "Desc_ZorblaxFrame_C"
GEAR = "Desc_ZorblaxGear_C"
SOLID_ZORBLAX = "Desc_SolidZorblax_C"

BONDED = "Recipe_Alternate_BondedZorblaxPlate_C"
GEAR_ALT = "Recipe_Alternate_ZorblaxGear_C"


@pytest.fixture
def game_data() -> GameData:
    return parse_game_data(FIXTURE)


@pytest.fixture
def cyclic_game_data() -> GameData:
    return parse_game_data(CYCLIC_FIXTURE)


# ---------------------------------------------------------------------------
# Recipe-set counts per alternate combination
# ---------------------------------------------------------------------------


def test_no_alternates_gives_one_chain(game_data: GameData) -> None:
    result = select_recipes([FRAME], set(), game_data)
    assert result.failure is None
    assert len(result.selections) == 1


def test_bonded_alternate_gives_two_chains(game_data: GameData) -> None:
    """With Bonded unlocked, RZP has two recipe choices → two chains."""
    result = select_recipes([FRAME], {BONDED}, game_data)
    assert result.failure is None
    assert len(result.selections) == 2


# ---------------------------------------------------------------------------
# Phase 1 failure: item only produceable via locked alternate
# ---------------------------------------------------------------------------


def test_phase1_failure_when_only_alternate_locked(game_data: GameData) -> None:
    result = select_recipes([GEAR], set(), game_data)
    assert isinstance(result.failure, Phase1Failure)
    assert result.failure.item_class == GEAR
    assert len(result.selections) == 0


def test_phase1_success_when_alternate_unlocked(game_data: GameData) -> None:
    result = select_recipes([GEAR], {GEAR_ALT}, game_data)
    assert result.failure is None
    assert len(result.selections) == 1


# ---------------------------------------------------------------------------
# All leaf items are raw resources (no available producer)
# ---------------------------------------------------------------------------


def test_all_leaf_items_are_raw_resources(game_data: GameData) -> None:
    result = select_recipes([FRAME], {BONDED}, game_data)
    assert result.failure is None

    for sel in result.selections:
        produced = {p.item_class for r in sel.recipes.values() for p in r.products}
        consumed = {i.item_class for r in sel.recipes.values() for i in r.ingredients}
        raw_inputs = consumed - produced

        for item_class in raw_inputs:
            has_recipe = any(
                not r.is_build_gun and any(p.item_class == item_class for p in r.products)
                for r in game_data.recipes
            )
            assert not has_recipe, f"'{item_class}' has a recipe but was treated as a raw input"


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------


def test_cyclic_chain_is_flagged(cyclic_game_data: GameData) -> None:
    """AquaCycle consumes and produces AquaZorblax — must be flagged as cyclic."""
    result = select_recipes([SOLID_ZORBLAX], set(), cyclic_game_data)
    assert result.failure is None
    assert len(result.selections) == 1
    assert result.selections[0].has_cycle is True


def test_acyclic_chain_not_flagged(game_data: GameData) -> None:
    result = select_recipes([FRAME], set(), game_data)
    assert result.selections[0].has_cycle is False


# ---------------------------------------------------------------------------
# Byproduct routing
# ---------------------------------------------------------------------------


def test_byproduct_routing_records_dependency(cyclic_game_data: GameData) -> None:
    """AquaZorblax is an ingredient AND a product of AquaCycle — byproduct routing fires."""
    result = select_recipes([SOLID_ZORBLAX], set(), cyclic_game_data)
    sel = result.selections[0]
    assert "Desc_AquaZorblax_C" in sel.byproduct_deps
    assert sel.byproduct_deps["Desc_AquaZorblax_C"] == "Recipe_AquaCycle_C"


# ---------------------------------------------------------------------------
# Chain limit / cap
# ---------------------------------------------------------------------------


def test_chain_limit_respected(game_data: GameData) -> None:
    result = select_recipes([FRAME], {BONDED}, game_data, chain_limit=1)
    assert len(result.selections) == 1
    assert result.cap_reached is True


def test_cap_not_reached_when_under_limit(game_data: GameData) -> None:
    result = select_recipes([FRAME], {BONDED}, game_data)
    assert result.cap_reached is False


# ---------------------------------------------------------------------------
# Minimal recipe sets
# ---------------------------------------------------------------------------


def test_no_alternates_chain_contains_correct_recipes(game_data: GameData) -> None:
    """Standard chain for ZorblaxFrame uses exactly these four recipes."""
    result = select_recipes([FRAME], set(), game_data)
    assert set(result.selections[0].recipes.keys()) == {
        "Recipe_ZorblaxFrame_C",
        "Recipe_ReinforcedZorblaxPlate_C",
        "Recipe_ZorblaxPlate_C",
        "Recipe_ZorblaxRod_C",
    }


def test_bonded_chain_uses_alternate_recipe(game_data: GameData) -> None:
    """One of the two chains when Bonded is unlocked should use the alternate."""
    result = select_recipes([FRAME], {BONDED}, game_data)
    recipe_sets = [set(sel.recipes.keys()) for sel in result.selections]
    assert any(BONDED in rs for rs in recipe_sets)


# ---------------------------------------------------------------------------
# Multiple desired outputs
# ---------------------------------------------------------------------------


def test_multiple_desired_outputs(game_data: GameData) -> None:
    """Asking for both ZorblaxFrame and ZorblaxGear (with alt) returns chains covering both."""
    result = select_recipes([FRAME, GEAR], {GEAR_ALT}, game_data)
    assert result.failure is None
    assert len(result.selections) >= 1

    for sel in result.selections:
        produced = {p.item_class for r in sel.recipes.values() for p in r.products}
        assert FRAME in produced
        assert GEAR in produced
