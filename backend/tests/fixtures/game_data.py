"""Minimal fixture data for parser tests.

Uses entirely fictional item/machine/recipe names and class names.
No strings from the actual game data files are present here.

The NativeClass type identifiers (FGItemDescriptor, FGRecipe, etc.) and
the BP_BuildGun marker are retained because they are also hardcoded in
parser.py as the detection logic — the fixture cannot test that logic
without referencing the same strings.

Format matches the real en-CA.json structure exactly:
  mIngredients / mProduct entries:
    (ItemClass="/Script/Engine.BlueprintGeneratedClass'/Game/.../Desc_X.Desc_X_C'",Amount=N)
  mProducedIn:
    ("/Game/.../Build_X.Build_X_C")

Fictional universe — "Zorblax" materials processed in a "Fabricator" or "Assemblatron":

  Desc_Zorblax_C            "Zorblax"                   primary raw material
  Desc_ZorblaxRod_C         "Zorblax Rod"               simple shaped part
  Desc_ZorblaxPlate_C       "Zorblax Plate"             simple flat part
  Desc_Sprongite_C          "Sprongite"                 secondary material
  Desc_ReinforcedZorblaxPlate_C  "Reinforced Zorblax Plate"   composite part
  Desc_ZorblaxFrame_C       "Zorblax Frame"             complex assembly
  Desc_OreZorblax_C         "Zorblax Ore"               raw resource

Per-minute rates (amount * 60 / duration_s):

  ZorblaxRod recipe       (duration=4s):   1*60/4  = 15.0/min  in,  15.0/min  out
  ZorblaxPlate recipe     (duration=6s):   3*60/6  = 30.0/min  in,  20.0/min  out
  Bonded alt recipe       (duration=32s): 10*60/32 = 18.75/min plate in,
                                          20*60/32 = 37.50/min Sprongite in,
                                           3*60/32 =  5.625/min RZP out
  ZorblaxFrame recipe     (duration=60s):  3*60/60 =  3.0/min  RZP in,
                                          12*60/60 = 12.0/min  rod in,
                                           2*60/60 =  2.0/min  frame out
"""

_GAME_ROOT = "/Game/FicSolverGame"


def _item_ref(cls: str, amt: int | float) -> str:
    """One ItemClass entry in the en-CA.json format (fictional paths)."""
    folder = cls.replace("Desc_", "").replace("_C", "")
    path = f"{_GAME_ROOT}/Resource/Parts/{folder}/{cls[:-2]}"
    return f"(ItemClass=\"/Script/Engine.BlueprintGeneratedClass'{path}.{cls}'\",Amount={amt})"


def _machine_ref(cls: str) -> str:
    """One mProducedIn path entry (fictional paths)."""
    folder = cls.replace("Build_", "").replace("_C", "")
    asset = cls[:-2]
    return f'"{_GAME_ROOT}/Buildable/Factory/{folder}/{asset}.{cls}"'


FIXTURE: list[dict] = [
    # ------------------------------------------------------------------
    # Items — FGItemDescriptor bucket
    # ------------------------------------------------------------------
    {
        "NativeClass": "/Script/CoreUObject.Class'/Script/FicSolverGame.FGItemDescriptor'",
        "Classes": [
            {"ClassName": "Desc_Zorblax_C", "mDisplayName": "Zorblax"},
            {"ClassName": "Desc_ZorblaxRod_C", "mDisplayName": "Zorblax Rod"},
            {"ClassName": "Desc_ZorblaxPlate_C", "mDisplayName": "Zorblax Plate"},
            {"ClassName": "Desc_Sprongite_C", "mDisplayName": "Sprongite"},
            {
                "ClassName": "Desc_ReinforcedZorblaxPlate_C",
                "mDisplayName": "Reinforced Zorblax Plate",
            },
            {"ClassName": "Desc_ZorblaxFrame_C", "mDisplayName": "Zorblax Frame"},
        ],
    },
    # ------------------------------------------------------------------
    # Raw resources — FGResourceDescriptor bucket
    # ------------------------------------------------------------------
    {
        "NativeClass": "/Script/CoreUObject.Class'/Script/FicSolverGame.FGResourceDescriptor'",
        "Classes": [
            {"ClassName": "Desc_OreZorblax_C", "mDisplayName": "Zorblax Ore"},
        ],
    },
    # ------------------------------------------------------------------
    # Machines — FGBuildableManufacturer bucket
    # ------------------------------------------------------------------
    {
        "NativeClass": "/Script/CoreUObject.Class'/Script/FicSolverGame.FGBuildableManufacturer'",
        "Classes": [
            {"ClassName": "Build_FabricatorMk1_C", "mDisplayName": "Fabricator"},
            {"ClassName": "Build_AssemblatronMk1_C", "mDisplayName": "Assemblatron"},
        ],
    },
    # ------------------------------------------------------------------
    # Recipes — FGRecipe bucket
    # ------------------------------------------------------------------
    {
        "NativeClass": "/Script/CoreUObject.Class'/Script/FicSolverGame.FGRecipe'",
        "Classes": [
            # Single-ingredient, single-product (Fabricator)
            # 1 Zorblax → 1 ZorblaxRod per 4 s  →  15/min each
            {
                "ClassName": "Recipe_ZorblaxRod_C",
                "mDisplayName": "Zorblax Rod",
                "mIngredients": f"({_item_ref('Desc_Zorblax_C', 1)})",
                "mProduct": f"({_item_ref('Desc_ZorblaxRod_C', 1)})",
                "mManufactoringDuration": "4.000000",
                "mProducedIn": f"({_machine_ref('Build_FabricatorMk1_C')})",
            },
            # Single-ingredient, single-product (Fabricator)
            # 3 Zorblax → 2 ZorblaxPlate per 6 s  →  30/min in, 20/min out
            {
                "ClassName": "Recipe_ZorblaxPlate_C",
                "mDisplayName": "Zorblax Plate",
                "mIngredients": f"({_item_ref('Desc_Zorblax_C', 3)})",
                "mProduct": f"({_item_ref('Desc_ZorblaxPlate_C', 2)})",
                "mManufactoringDuration": "6.000000",
                "mProducedIn": f"({_machine_ref('Build_FabricatorMk1_C')})",
            },
            # Alternate recipe — two ingredients (Assemblatron)
            # 10 ZorblaxPlate + 20 Sprongite → 3 RZP per 32 s  →  18.75+37.5 → 5.625/min
            {
                "ClassName": "Recipe_Alternate_BondedZorblaxPlate_C",
                "mDisplayName": "Alternate: Bonded Zorblax Plate",
                "mIngredients": (
                    f"({_item_ref('Desc_ZorblaxPlate_C', 10)},{_item_ref('Desc_Sprongite_C', 20)})"
                ),
                "mProduct": f"({_item_ref('Desc_ReinforcedZorblaxPlate_C', 3)})",
                "mManufactoringDuration": "32.000000",
                "mProducedIn": f"({_machine_ref('Build_AssemblatronMk1_C')})",
            },
            # Two-ingredient, one-product (Assemblatron)
            # 3 RZP + 12 ZorblaxRod → 2 ZorblaxFrame per 60 s  →  3+12 → 2/min
            {
                "ClassName": "Recipe_ZorblaxFrame_C",
                "mDisplayName": "Zorblax Frame",
                "mIngredients": (
                    f"({_item_ref('Desc_ReinforcedZorblaxPlate_C', 3)},"
                    f"{_item_ref('Desc_ZorblaxRod_C', 12)})"
                ),
                "mProduct": f"({_item_ref('Desc_ZorblaxFrame_C', 2)})",
                "mManufactoringDuration": "60.000000",
                "mProducedIn": f"({_machine_ref('Build_AssemblatronMk1_C')})",
            },
            # Build-gun recipe — must be flagged is_build_gun=True
            # BP_BuildGun is retained: it is also hardcoded in parser.py as the detection marker.
            {
                "ClassName": "Recipe_Build_FabricatorMk1_C",
                "mDisplayName": "Fabricator",
                "mIngredients": f"({_item_ref('Desc_ZorblaxPlate_C', 4)})",
                "mProduct": (
                    "(ItemClass=\"/Script/Engine.BlueprintGeneratedClass'"
                    f"{_GAME_ROOT}/Buildable/Factory/FabricatorMk1"
                    "/Build_FabricatorMk1.Build_FabricatorMk1_C'\",Amount=1)"
                ),
                "mManufactoringDuration": "0.000000",
                "mProducedIn": (f'("{_GAME_ROOT}/Equipment/BuildGun/BP_BuildGun.BP_BuildGun_C")'),
            },
        ],
    },
]
