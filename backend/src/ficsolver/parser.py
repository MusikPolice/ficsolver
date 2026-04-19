"""Parse en-CA.json game data into typed Python models.

The file is UTF-16 encoded (with BOM) and contains a JSON array.  Each
element is a ``NativeClass`` bucket — a dict with two keys:

* ``"NativeClass"`` — an Unreal class path string used to identify the bucket type
* ``"Classes"``     — an array of item/recipe/machine dicts

``mIngredients`` and ``mProduct`` are *encoded* Unreal Engine property-text
strings, not nested JSON.  Real format (outer delimiter ``"``, inner ``'``):

    (ItemClass="/Script/Engine.BlueprintGeneratedClass'/Game/.../Desc_X.Desc_X_C'",Amount=N)

``mProducedIn`` is a parenthesised, comma-separated list of quoted asset paths:

    ("/Game/.../Build_XMk1.Build_XMk1_C","/Game/.../WorkBench.BP_WorkBenchComponent_C")

Amounts in the raw data are *per-cycle*; we convert to per-minute via
``amount * 60 / mManufactoringDuration``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ficsolver.models import GameData, Item, ItemAmount, Machine, Recipe

# ---------------------------------------------------------------------------
# NativeClass filters
# ---------------------------------------------------------------------------

#: NativeClass substrings that indicate item-descriptor buckets
_ITEM_NATIVE_CLASSES: frozenset[str] = frozenset(
    {
        "FGItemDescriptor",
        "FGResourceDescriptor",
        "FGEquipmentDescriptor",
        "FGConsumableDescriptor",
        "FGAmmoTypeInstantHit",
        "FGAmmoTypeSpreadshot",
        "FGBuildingDescriptor",
        "FGVehicleDescriptor",
        "FGPoleDescriptor",
    }
)

#: NativeClass substring for recipe buckets
_RECIPE_NATIVE_CLASS = "FGRecipe"

#: NativeClass substrings for machine/manufacturer buckets
_MACHINE_NATIVE_CLASSES: frozenset[str] = frozenset(
    {
        "FGBuildableManufacturer",
        "FGBuildableManufacturerVariablePower",
    }
)

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

# Matches one ingredient/product tuple inside the encoded property-text string.
# Captures (1) short class name, e.g. "Desc_IronPlate_C", and (2) cycle amount.
#
# Real game format (en-CA.json):
#   ItemClass="/Script/Engine.BlueprintGeneratedClass'/Game/.../Desc_X.Desc_X_C'",Amount=3
#
# The outer delimiter is " and the inner path is wrapped in '.
_ITEM_AMOUNT_RE = re.compile(r"""ItemClass="[^"']*'[^']*\.(\w+)'[^"]*",Amount=([\d.]+)""")

# Matches the first class path inside mProducedIn, capturing the short class name.
# Example: (/Game/.../Build_ConstructorMk1.Build_ConstructorMk1_C)
_PRODUCED_IN_RE = re.compile(r"/[^,)]+\.(\w+_C)")

_BUILD_GUN_MARKER = "BP_BuildGun"


def _matches_native_class(native_class: str, names: frozenset[str]) -> bool:
    return any(name in native_class for name in names)


def _parse_item_amounts(
    encoded: str, duration_sec: float, fluid_classes: frozenset[str]
) -> list[ItemAmount]:
    """Return per-minute ``ItemAmount`` entries from an encoded property string.

    Liquid and gas amounts in en-CA.json are stored at x1000 scale (millilitres /
    millicubic-metres) relative to the m³ values shown in-game.  Divide those by
    1000 before converting to per-minute rates.
    """
    results: list[ItemAmount] = []
    for match in _ITEM_AMOUNT_RE.finditer(encoded):
        class_name = match.group(1)
        cycle_amount = float(match.group(2))
        if class_name in fluid_classes:
            cycle_amount /= 1000.0
        rate_per_min = cycle_amount * 60.0 / duration_sec
        results.append(ItemAmount(item_class=class_name, amount_per_min=rate_per_min))
    return results


def _parse_machine_class(produced_in: str) -> str:
    """Extract the short class name of the first machine in ``mProducedIn``."""
    match = _PRODUCED_IN_RE.search(produced_in)
    return match.group(1) if match else ""


# ---------------------------------------------------------------------------
# Per-bucket parsers
# ---------------------------------------------------------------------------


def _parse_items(classes: list[dict[str, Any]], is_raw_resource: bool = False) -> dict[str, Item]:
    items: dict[str, Item] = {}
    for cls in classes:
        class_name: str = cls.get("ClassName", "")
        display_name: str = cls.get("mDisplayName", class_name)
        mform: str = cls.get("mForm", "")
        if class_name:
            items[class_name] = Item(
                class_name=class_name,
                display_name=display_name,
                is_raw_resource=is_raw_resource,
                is_fluid=mform in ("RF_LIQUID", "RF_GAS"),
            )
    return items


def _parse_machines(classes: list[dict[str, Any]]) -> dict[str, Machine]:
    machines: dict[str, Machine] = {}
    for cls in classes:
        class_name: str = cls.get("ClassName", "")
        display_name: str = cls.get("mDisplayName", class_name)
        if class_name:
            machines[class_name] = Machine(class_name=class_name, display_name=display_name)
    return machines


def _parse_recipes(classes: list[dict[str, Any]], fluid_classes: frozenset[str]) -> list[Recipe]:
    recipes: list[Recipe] = []
    for cls in classes:
        class_name: str = cls.get("ClassName", "")
        if not class_name:
            continue

        display_name: str = cls.get("mDisplayName", class_name)
        produced_in: str = cls.get("mProducedIn", "")
        raw_ingredients: str = cls.get("mIngredients", "")
        raw_products: str = cls.get("mProduct", "")

        try:
            duration = float(cls.get("mManufactoringDuration", 0))
        except (ValueError, TypeError):
            duration = 0.0

        is_build_gun = _BUILD_GUN_MARKER in produced_in
        is_alternate = class_name.startswith("Recipe_Alternate_") or str(display_name).startswith(
            "Alternate: "
        )

        machine_class = _parse_machine_class(produced_in)

        if duration > 0:
            ingredients = _parse_item_amounts(raw_ingredients, duration, fluid_classes)
            products = _parse_item_amounts(raw_products, duration, fluid_classes)
        else:
            ingredients = []
            products = []

        recipes.append(
            Recipe(
                class_name=class_name,
                display_name=display_name,
                machine_class=machine_class,
                ingredients=ingredients,
                products=products,
                duration=duration,
                is_alternate=is_alternate,
                is_build_gun=is_build_gun,
            )
        )
    return recipes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_game_data(data: list[dict[str, Any]]) -> GameData:
    """Parse a decoded en-CA.json array into a :class:`GameData` instance.

    Items are parsed first so that fluid item classes are known before recipes
    are parsed (recipe amounts for fluids must be divided by 1000).
    """
    items: dict[str, Item] = {}
    machines: dict[str, Machine] = {}
    recipes: list[Recipe] = []

    # First pass: items and machines (needed to identify fluids before recipes).
    for bucket in data:
        native_class: str = bucket.get("NativeClass", "")
        classes: list[dict[str, Any]] = bucket.get("Classes", [])

        if _matches_native_class(native_class, _ITEM_NATIVE_CLASSES):
            is_raw = "FGResourceDescriptor" in native_class
            items.update(_parse_items(classes, is_raw_resource=is_raw))
        elif _matches_native_class(native_class, _MACHINE_NATIVE_CLASSES):
            machines.update(_parse_machines(classes))

    fluid_classes: frozenset[str] = frozenset(cn for cn, it in items.items() if it.is_fluid)

    # Second pass: recipes, now that fluid item classes are known.
    for bucket in data:
        native_class = bucket.get("NativeClass", "")
        classes = bucket.get("Classes", [])
        if _RECIPE_NATIVE_CLASS in native_class:
            recipes.extend(_parse_recipes(classes, fluid_classes))

    return GameData(items=items, machines=machines, recipes=recipes)


def load_game_data(path: Path) -> GameData:
    """Load and parse en-CA.json from *path*.

    The real game file is UTF-16 LE with a BOM; this function detects the
    encoding via the BOM and falls back to UTF-8 for test fixtures.
    """
    raw = path.read_bytes()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8")
    return parse_game_data(json.loads(text))
