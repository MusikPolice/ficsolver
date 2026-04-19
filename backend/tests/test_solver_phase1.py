"""Tests for solver Phase 1: DFS recipe selection.

Uses the Zorblax universe fixture.  Key recipe paths:

  ZorblaxFrame
    → ReinforcedZorblaxPlate (standard: Recipe_ReinforcedZorblaxPlate_C)
       OR Bonded alt (Recipe_Alternate_BondedZorblaxPlate_C, needs Sprongite)
    → ZorblaxRod

  ZorblaxGear — only via alternate Recipe_Alternate_ZorblaxGear_C
"""

import pytest

from ficsolver.models import GameData, Item, ItemAmount, Recipe
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


# ---------------------------------------------------------------------------
# Raw resource with Converter-style recipe: mine-it branch must appear
# ---------------------------------------------------------------------------


def _make_converter_game_data() -> GameData:
    """Minimal universe: Ore (raw) → Ingot via smelt; also Ore ← SAM via converter."""
    ORE = "Desc_Ore_C"
    INGOT = "Desc_Ingot_C"
    SAM = "Desc_SAM_C"
    return GameData(
        items={
            ORE: Item(ORE, "Ore", is_raw_resource=True),
            INGOT: Item(INGOT, "Ingot"),
            SAM: Item(SAM, "SAM", is_raw_resource=True),
        },
        machines={},
        recipes=[
            Recipe(
                class_name="Recipe_Smelt_C",
                display_name="Smelt",
                machine_class="Build_Smelter_C",
                ingredients=[ItemAmount(ORE, 30)],
                products=[ItemAmount(INGOT, 30)],
                duration=2,
                is_alternate=False,
                is_build_gun=False,
            ),
            Recipe(
                class_name="Recipe_OreFromSAM_C",
                display_name="Ore from SAM",
                machine_class="Build_Converter_C",
                # Standard (non-alternate) recipe — the bug was that this made Ore
                # no longer treated as a raw resource, hiding the simple mine-it chain.
                ingredients=[ItemAmount(SAM, 10)],
                products=[ItemAmount(ORE, 15)],
                duration=4,
                is_alternate=False,
                is_build_gun=False,
            ),
        ],
    )


def test_raw_resource_with_converter_also_yields_mine_branch() -> None:
    """When a raw resource also has a standard Converter recipe producing it,
    the DFS must yield a branch where it is simply mined (no Converter recipe)
    in addition to branches where the Converter is used."""
    gd = _make_converter_game_data()
    result = select_recipes(["Desc_Ingot_C"], set(), gd)
    assert result.failure is None

    recipe_sets = [set(sel.recipes.keys()) for sel in result.selections]
    # Mine-it branch: only the smelt recipe (Ore treated as raw input)
    assert {"Recipe_Smelt_C"} in recipe_sets
    # Converter branch: smelt + converter
    assert {"Recipe_Smelt_C", "Recipe_OreFromSAM_C"} in recipe_sets


def test_raw_resource_converter_branch_count() -> None:
    """Exactly two selections: mine-it and converter."""
    gd = _make_converter_game_data()
    result = select_recipes(["Desc_Ingot_C"], set(), gd)
    assert len(result.selections) == 2


# ---------------------------------------------------------------------------
# Declared available inputs are treated as terminals in the DFS
# ---------------------------------------------------------------------------


def _make_declared_input_game_data() -> GameData:
    """Minimal universe: Ore (raw) → Ingot (smelt) → Plate (press)."""
    ORE = "Desc_Ore_C"
    INGOT = "Desc_Ingot_C"
    PLATE = "Desc_Plate_C"
    return GameData(
        items={
            ORE: Item(ORE, "Ore", is_raw_resource=True),
            INGOT: Item(INGOT, "Ingot"),
            PLATE: Item(PLATE, "Plate"),
        },
        machines={},
        recipes=[
            Recipe(
                class_name="Recipe_Smelt_C",
                display_name="Smelt",
                machine_class="Build_Smelter_C",
                ingredients=[ItemAmount(ORE, 30)],
                products=[ItemAmount(INGOT, 30)],
                duration=2,
                is_alternate=False,
                is_build_gun=False,
            ),
            Recipe(
                class_name="Recipe_Press_C",
                display_name="Press",
                machine_class="Build_Constructor_C",
                ingredients=[ItemAmount(INGOT, 30)],
                products=[ItemAmount(PLATE, 20)],
                duration=3,
                is_alternate=False,
                is_build_gun=False,
            ),
        ],
    )


def test_declared_input_without_any_gives_one_chain() -> None:
    """Without declared inputs, only the full mine→smelt→press chain exists."""
    gd = _make_declared_input_game_data()
    result = select_recipes(["Desc_Plate_C"], set(), gd)
    assert result.failure is None
    assert len(result.selections) == 1
    assert "Recipe_Smelt_C" in result.selections[0].recipes


def test_declared_input_adds_skip_recipe_branch() -> None:
    """Declaring Ingot as an available input adds a branch where Ingot is taken
    from stock (only Press recipe needed) alongside the full mine+smelt branch."""
    gd = _make_declared_input_game_data()
    result = select_recipes(["Desc_Plate_C"], set(), gd, available_inputs={"Desc_Ingot_C"})
    assert result.failure is None

    recipe_sets = [set(sel.recipes.keys()) for sel in result.selections]
    # Use-declared-input branch: only the press recipe
    assert {"Recipe_Press_C"} in recipe_sets
    # Full chain branch: smelt + press
    assert {"Recipe_Smelt_C", "Recipe_Press_C"} in recipe_sets


def test_declared_input_gives_two_selections() -> None:
    """Exactly two selections when an intermediate item is declared as available."""
    gd = _make_declared_input_game_data()
    result = select_recipes(["Desc_Plate_C"], set(), gd, available_inputs={"Desc_Ingot_C"})
    assert len(result.selections) == 2
