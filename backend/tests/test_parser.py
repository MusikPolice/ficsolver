"""Tests for ficsolver.parser.

All fixture data uses fictional names (Zorblax universe) — no player-facing
strings from the actual game files appear here or in the fixture module.
"""

import json

import pytest

from ficsolver.models import GameData
from ficsolver.parser import load_game_data, parse_game_data
from tests.fixtures.game_data import FIXTURE

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def game_data() -> GameData:
    return parse_game_data(FIXTURE)


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


def test_items_parsed(game_data: GameData) -> None:
    assert "Desc_Zorblax_C" in game_data.items
    assert "Desc_ZorblaxRod_C" in game_data.items
    assert "Desc_ZorblaxPlate_C" in game_data.items
    assert "Desc_Sprongite_C" in game_data.items
    assert "Desc_ReinforcedZorblaxPlate_C" in game_data.items
    assert "Desc_ZorblaxFrame_C" in game_data.items


def test_item_display_names(game_data: GameData) -> None:
    assert game_data.items["Desc_Zorblax_C"].display_name == "Zorblax"
    assert game_data.items["Desc_ZorblaxFrame_C"].display_name == "Zorblax Frame"


def test_resource_descriptor_bucket_parsed(game_data: GameData) -> None:
    """FGResourceDescriptor bucket should also yield items."""
    assert "Desc_OreZorblax_C" in game_data.items
    assert game_data.items["Desc_OreZorblax_C"].display_name == "Zorblax Ore"


# ---------------------------------------------------------------------------
# Machines
# ---------------------------------------------------------------------------


def test_machines_parsed(game_data: GameData) -> None:
    assert "Build_FabricatorMk1_C" in game_data.machines
    assert "Build_AssemblatronMk1_C" in game_data.machines


def test_machine_display_names(game_data: GameData) -> None:
    assert game_data.machines["Build_FabricatorMk1_C"].display_name == "Fabricator"
    assert game_data.machines["Build_AssemblatronMk1_C"].display_name == "Assemblatron"


# ---------------------------------------------------------------------------
# Recipes — helper
# ---------------------------------------------------------------------------


def _recipe(game_data: GameData, class_name: str):  # type: ignore[return]
    for r in game_data.recipes:
        if r.class_name == class_name:
            return r
    pytest.fail(f"Recipe {class_name!r} not found in parsed data")


# ---------------------------------------------------------------------------
# Per-minute rates
# ---------------------------------------------------------------------------


def test_zorblax_rod_ingredient_rate(game_data: GameData) -> None:
    """ZorblaxRod recipe: 1 Zorblax per 4 s → 15 / min."""
    recipe = _recipe(game_data, "Recipe_ZorblaxRod_C")
    assert len(recipe.ingredients) == 1
    ing = recipe.ingredients[0]
    assert ing.item_class == "Desc_Zorblax_C"
    assert ing.amount_per_min == pytest.approx(15.0)


def test_zorblax_rod_product_rate(game_data: GameData) -> None:
    """ZorblaxRod recipe: 1 ZorblaxRod per 4 s → 15 / min."""
    recipe = _recipe(game_data, "Recipe_ZorblaxRod_C")
    assert len(recipe.products) == 1
    prod = recipe.products[0]
    assert prod.item_class == "Desc_ZorblaxRod_C"
    assert prod.amount_per_min == pytest.approx(15.0)


def test_zorblax_plate_ingredient_rate(game_data: GameData) -> None:
    """ZorblaxPlate recipe: 3 Zorblax per 6 s → 30 / min."""
    recipe = _recipe(game_data, "Recipe_ZorblaxPlate_C")
    ing = recipe.ingredients[0]
    assert ing.item_class == "Desc_Zorblax_C"
    assert ing.amount_per_min == pytest.approx(30.0)


def test_zorblax_plate_product_rate(game_data: GameData) -> None:
    """ZorblaxPlate recipe: 2 ZorblaxPlate per 6 s → 20 / min."""
    recipe = _recipe(game_data, "Recipe_ZorblaxPlate_C")
    prod = recipe.products[0]
    assert prod.item_class == "Desc_ZorblaxPlate_C"
    assert prod.amount_per_min == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# Multi-ingredient recipe
# ---------------------------------------------------------------------------


def test_bonded_plate_has_two_ingredients(game_data: GameData) -> None:
    recipe = _recipe(game_data, "Recipe_Alternate_BondedZorblaxPlate_C")
    assert len(recipe.ingredients) == 2


def test_bonded_plate_ingredient_rates(game_data: GameData) -> None:
    """Bonded alt: 10 ZorblaxPlate + 20 Sprongite per 32 s → 18.75 + 37.5 / min."""
    recipe = _recipe(game_data, "Recipe_Alternate_BondedZorblaxPlate_C")
    by_class = {i.item_class: i.amount_per_min for i in recipe.ingredients}
    assert by_class["Desc_ZorblaxPlate_C"] == pytest.approx(18.75)
    assert by_class["Desc_Sprongite_C"] == pytest.approx(37.5)


def test_bonded_plate_product_rate(game_data: GameData) -> None:
    """Bonded alt: 3 RZP per 32 s → 5.625 / min."""
    recipe = _recipe(game_data, "Recipe_Alternate_BondedZorblaxPlate_C")
    assert len(recipe.products) == 1
    assert recipe.products[0].item_class == "Desc_ReinforcedZorblaxPlate_C"
    assert recipe.products[0].amount_per_min == pytest.approx(5.625)


def test_zorblax_frame_has_two_ingredients(game_data: GameData) -> None:
    recipe = _recipe(game_data, "Recipe_ZorblaxFrame_C")
    assert len(recipe.ingredients) == 2


def test_zorblax_frame_ingredient_rates(game_data: GameData) -> None:
    """ZorblaxFrame: 3 RZP + 12 ZorblaxRod per 60 s → 3 + 12 / min."""
    recipe = _recipe(game_data, "Recipe_ZorblaxFrame_C")
    by_class = {i.item_class: i.amount_per_min for i in recipe.ingredients}
    assert by_class["Desc_ReinforcedZorblaxPlate_C"] == pytest.approx(3.0)
    assert by_class["Desc_ZorblaxRod_C"] == pytest.approx(12.0)


def test_zorblax_frame_product_rate(game_data: GameData) -> None:
    """ZorblaxFrame: 2 frames per 60 s → 2 / min."""
    recipe = _recipe(game_data, "Recipe_ZorblaxFrame_C")
    assert recipe.products[0].item_class == "Desc_ZorblaxFrame_C"
    assert recipe.products[0].amount_per_min == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Alternate recipe flagging
# ---------------------------------------------------------------------------


def test_alternate_flagged_by_class_name(game_data: GameData) -> None:
    recipe = _recipe(game_data, "Recipe_Alternate_BondedZorblaxPlate_C")
    assert recipe.is_alternate is True


def test_non_alternate_not_flagged(game_data: GameData) -> None:
    assert _recipe(game_data, "Recipe_ZorblaxPlate_C").is_alternate is False
    assert _recipe(game_data, "Recipe_ZorblaxFrame_C").is_alternate is False


# ---------------------------------------------------------------------------
# Machine assignment
# ---------------------------------------------------------------------------


def test_fabricator_recipe_machine(game_data: GameData) -> None:
    recipe = _recipe(game_data, "Recipe_ZorblaxRod_C")
    assert recipe.machine_class == "Build_FabricatorMk1_C"


def test_assemblatron_recipe_machine(game_data: GameData) -> None:
    recipe = _recipe(game_data, "Recipe_ZorblaxFrame_C")
    assert recipe.machine_class == "Build_AssemblatronMk1_C"


# ---------------------------------------------------------------------------
# Build-gun recipe flagging
# ---------------------------------------------------------------------------


def test_build_gun_recipe_flagged(game_data: GameData) -> None:
    recipe = _recipe(game_data, "Recipe_Build_FabricatorMk1_C")
    assert recipe.is_build_gun is True


def test_production_recipes_not_build_gun(game_data: GameData) -> None:
    for class_name in ("Recipe_ZorblaxPlate_C", "Recipe_ZorblaxFrame_C"):
        assert _recipe(game_data, class_name).is_build_gun is False


def test_recipe_count(game_data: GameData) -> None:
    """All five fixture recipes should be returned."""
    names = {r.class_name for r in game_data.recipes}
    assert names == {
        "Recipe_ZorblaxRod_C",
        "Recipe_ZorblaxPlate_C",
        "Recipe_Alternate_BondedZorblaxPlate_C",
        "Recipe_ZorblaxFrame_C",
        "Recipe_Build_FabricatorMk1_C",
    }


# ---------------------------------------------------------------------------
# load_game_data — file I/O and encoding
# ---------------------------------------------------------------------------


def test_load_game_data_utf8(tmp_path: pytest.TempPathFactory) -> None:
    """load_game_data should parse a UTF-8 JSON file correctly."""
    p = tmp_path / "en-CA.json"  # type: ignore[operator]
    p.write_bytes(json.dumps(FIXTURE).encode("utf-8"))
    gd = load_game_data(p)
    assert "Desc_Zorblax_C" in gd.items
    assert any(r.class_name == "Recipe_ZorblaxPlate_C" for r in gd.recipes)


def test_load_game_data_utf16(tmp_path: pytest.TempPathFactory) -> None:
    """load_game_data should parse a UTF-16 LE file (real game format)."""
    p = tmp_path / "en-CA.json"  # type: ignore[operator]
    p.write_bytes(json.dumps(FIXTURE).encode("utf-16"))
    gd = load_game_data(p)
    assert "Desc_Zorblax_C" in gd.items
    assert any(r.class_name == "Recipe_ZorblaxPlate_C" for r in gd.recipes)
