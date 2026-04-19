"""Phase 2 solver tests: quantity calculation, machine counts, and clock speeds.

All tests use the Zorblax fixture universe defined in tests/fixtures/game_data.py.
Additional ad-hoc Recipe / GameData objects are built inline where the fixture
does not cover a specific behaviour (e.g. byproduct implicit outputs).

Per-minute rates for the fixture (amount * 60 / duration_s):

  ZorblaxRod        (4s):  in  15.0 Zorblax/min  →  out 15.0 Rod/min
  ZorblaxPlate      (6s):  in  30.0 Zorblax/min  →  out 20.0 Plate/min
  RZP std          (20s):  in   9.0 Plate/min    →  out  3.0 RZP/min
  RZP Bonded       (32s):  in  18.75 Plate/min
                           in  37.5  Sprongite/min →  out 5.625 RZP/min
  ZorblaxFrame     (60s):  in   3.0 RZP/min
                           in  12.0 Rod/min       →  out  2.0 Frame/min
  ZorblaxGear alt  (40s):  in   7.5 Rod/min       →  out  3.0 Gear/min
  AquaCycle        (10s):  in   6.0 Aqua/min      →  out  6.0 Solid/min
                                                       out  6.0 Aqua/min
"""

from ficsolver.models import (
    GameData,
    Item,
    ItemAmount,
    MachineGroup,
    Recipe,
    SolverChain,
)
from ficsolver.parser import parse_game_data
from ficsolver.solver import (
    Phase2Failure,
    RecipeSelection,
    calculate_quantities,
    select_recipes,
)
from tests.fixtures.game_data import CYCLIC_FIXTURE, FIXTURE

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FRAME = "Desc_ZorblaxFrame_C"
_RZP = "Desc_ReinforcedZorblaxPlate_C"
_ROD = "Desc_ZorblaxRod_C"
_PLATE = "Desc_ZorblaxPlate_C"
_ZORBLAX = "Desc_Zorblax_C"
_SPRONGITE = "Desc_Sprongite_C"
_GEAR = "Desc_ZorblaxGear_C"

_RECIPE_FRAME = "Recipe_ZorblaxFrame_C"
_RECIPE_RZP = "Recipe_ReinforcedZorblaxPlate_C"
_RECIPE_BONDED = "Recipe_Alternate_BondedZorblaxPlate_C"
_RECIPE_ROD = "Recipe_ZorblaxRod_C"
_RECIPE_PLATE = "Recipe_ZorblaxPlate_C"
_RECIPE_GEAR = "Recipe_Alternate_ZorblaxGear_C"

_AQUA = "Desc_AquaZorblax_C"
_SOLID = "Desc_SolidZorblax_C"
_RECIPE_AQUA = "Recipe_AquaCycle_C"


def _game_data() -> GameData:
    return parse_game_data(FIXTURE)


def _cyclic_game_data() -> GameData:
    return parse_game_data(CYCLIC_FIXTURE)


def _selection_standard_frame(gd: GameData) -> RecipeSelection:
    """Phase 1 selection for ZorblaxFrame using standard RZP recipe."""
    result = select_recipes([_FRAME], set(), gd)
    assert result.selections, "Phase 1 produced no selections"
    assert not result.selections[0].has_cycle
    return result.selections[0]


def _selection_bonded_frame(gd: GameData) -> RecipeSelection:
    """Phase 1 selection for ZorblaxFrame using Bonded (alternate) RZP recipe."""
    result = select_recipes([_FRAME], {_RECIPE_BONDED}, gd)
    bonded = [s for s in result.selections if _RECIPE_BONDED in s.recipes]
    assert bonded, "No Bonded selection found"
    return bonded[0]


def _selection_cyclic(gd: GameData) -> RecipeSelection:
    """Phase 1 selection for SolidZorblax (cyclic chain)."""
    result = select_recipes([_SOLID], set(), gd)
    assert result.selections
    assert result.selections[0].has_cycle
    return result.selections[0]


# ===========================================================================
# Standard ZorblaxFrame — acyclic, back-substitution
# ===========================================================================

TARGET_FRAME = 5.0


class TestStandardFrameRates:
    """Recipe rates for 5 ZorblaxFrame/min with standard RZP recipe."""

    def test_frame_recipe_rate(self) -> None:
        gd = _game_data()
        sel = _selection_standard_frame(gd)
        chain = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        assert isinstance(chain, SolverChain)
        mg = _group(chain, _RECIPE_FRAME)
        # rate = 5.0 / 2.0 = 2.5
        assert abs(mg.exact_recipe_rate - 2.5) < 1e-9

    def test_rzp_recipe_rate(self) -> None:
        gd = _game_data()
        sel = _selection_standard_frame(gd)
        chain = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        assert isinstance(chain, SolverChain)
        mg = _group(chain, _RECIPE_RZP)
        # Frame needs 3 RZP/min at rate 2.5 → demand 7.5; RZP produces 3.0/min → rate 2.5
        assert abs(mg.exact_recipe_rate - 2.5) < 1e-9

    def test_rod_recipe_rate(self) -> None:
        gd = _game_data()
        sel = _selection_standard_frame(gd)
        chain = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        assert isinstance(chain, SolverChain)
        mg = _group(chain, _RECIPE_ROD)
        # Frame at 2.5 consumes 12 Rod/min → demand 30; Rod produces 15/min → rate 2.0
        assert abs(mg.exact_recipe_rate - 2.0) < 1e-9

    def test_plate_recipe_rate(self) -> None:
        gd = _game_data()
        sel = _selection_standard_frame(gd)
        chain = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        assert isinstance(chain, SolverChain)
        mg = _group(chain, _RECIPE_PLATE)
        # RZP at 2.5 consumes 9 Plate/min → demand 22.5; Plate produces 20/min → rate 1.125
        assert abs(mg.exact_recipe_rate - 1.125) < 1e-9

    def test_raw_resource_consumption(self) -> None:
        gd = _game_data()
        sel = _selection_standard_frame(gd)
        chain = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        assert isinstance(chain, SolverChain)
        # Rod recipe: 2.0 * 15.0 = 30.0; Plate recipe: 1.125 * 30.0 = 33.75 → total 63.75
        assert abs(chain.raw_resource_consumption[_ZORBLAX] - 63.75) < 1e-9

    def test_no_implicit_outputs(self) -> None:
        gd = _game_data()
        sel = _selection_standard_frame(gd)
        chain = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        assert isinstance(chain, SolverChain)
        # Standard chain: all intermediates exactly balanced, no byproducts
        assert chain.implicit_outputs == {}

    def test_not_a_cycle(self) -> None:
        gd = _game_data()
        sel = _selection_standard_frame(gd)
        chain = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        assert isinstance(chain, SolverChain)
        assert not chain.has_cycle


# ===========================================================================
# Machine counts and clock speeds — acyclic standard chain
# ===========================================================================


def _standard_frame_chain() -> SolverChain:
    gd = _game_data()
    chain = calculate_quantities(_selection_standard_frame(gd), {_FRAME: TARGET_FRAME}, True, gd)
    assert isinstance(chain, SolverChain)
    return chain


class TestMachineCountsStandard:
    """Machine counts and clock speeds derived from exact recipe rates."""

    def test_frame_machine_count(self) -> None:
        # rate 2.5 → ceil(2.5) = 3
        assert _standard_frame_chain().machine_groups
        assert _group(_standard_frame_chain(), _RECIPE_FRAME).machine_count == 3

    def test_frame_clock_speed(self) -> None:
        # 2.5 / 3 = 83.33% → ceil = 84%
        assert _group(_standard_frame_chain(), _RECIPE_FRAME).clock_speed_pct == 84

    def test_rzp_machine_count(self) -> None:
        assert _group(_standard_frame_chain(), _RECIPE_RZP).machine_count == 3

    def test_rzp_clock_speed(self) -> None:
        assert _group(_standard_frame_chain(), _RECIPE_RZP).clock_speed_pct == 84

    def test_rod_machine_count(self) -> None:
        # rate 2.0 → ceil(2.0) = 2
        assert _group(_standard_frame_chain(), _RECIPE_ROD).machine_count == 2

    def test_rod_clock_speed(self) -> None:
        # 2.0 / 2 = 100%
        assert _group(_standard_frame_chain(), _RECIPE_ROD).clock_speed_pct == 100

    def test_plate_machine_count(self) -> None:
        # rate 1.125 → ceil(1.125) = 2
        assert _group(_standard_frame_chain(), _RECIPE_PLATE).machine_count == 2

    def test_plate_clock_speed(self) -> None:
        # 1.125 / 2 = 56.25% → ceil = 57%
        assert _group(_standard_frame_chain(), _RECIPE_PLATE).clock_speed_pct == 57


# ===========================================================================
# Clock rounding edge cases
# ===========================================================================


class TestClockRounding:
    """Clock speed must always round UP to the nearest whole percent."""

    def test_exactly_100_percent_stays_100(self) -> None:
        # Rod: rate 2.0 / count 2 = exactly 100%
        assert _group(_standard_frame_chain(), _RECIPE_ROD).clock_speed_pct == 100

    def test_fractional_rate_rounds_up(self) -> None:
        # Build a recipe where rate / count is a non-integer percentage.
        # Recipe: 10 Raw → 3 Processed (per minute, at 100%).
        # Target: 1 Processed/min → rate = 1/3 ≈ 0.333 → count 1, clock ceil(33.33) = 34%
        recipe = _make_recipe(
            "R_Test",
            ingredients=[("Desc_Raw_C", 10.0)],
            products=[("Desc_Proc_C", 3.0)],
        )
        gd = _make_game_data([recipe], raw_items=["Desc_Raw_C"])
        sel = RecipeSelection(recipes={"R_Test": recipe}, has_cycle=False)
        chain = calculate_quantities(sel, {"Desc_Proc_C": 1.0}, True, gd)
        assert isinstance(chain, SolverChain)
        mg = chain.machine_groups[0]
        assert mg.machine_count == 1
        assert mg.clock_speed_pct == 34  # ceil(33.33...)

    def test_whole_percentage_is_unchanged(self) -> None:
        # Rate 0.75 of 1 machine → 75.00% → ceil(75.0) = 75 (no rounding change)
        recipe = _make_recipe(
            "R_Test",
            ingredients=[("Desc_Raw_C", 4.0)],
            products=[("Desc_Proc_C", 4.0)],
        )
        gd = _make_game_data([recipe], raw_items=["Desc_Raw_C"])
        sel = RecipeSelection(recipes={"R_Test": recipe}, has_cycle=False)
        # 3 Proc/min with recipe producing 4/min → rate 0.75 → count 1, clock 75%
        chain = calculate_quantities(sel, {"Desc_Proc_C": 3.0}, True, gd)
        assert isinstance(chain, SolverChain)
        assert chain.machine_groups[0].clock_speed_pct == 75


# ===========================================================================
# clocking_available=False
# ===========================================================================


class TestClockingUnavailable:
    """When clocking is unavailable all machine groups report 100% clock speed."""

    def test_all_groups_report_100_percent(self) -> None:
        gd = _game_data()
        chain = calculate_quantities(
            _selection_standard_frame(gd), {_FRAME: TARGET_FRAME}, False, gd
        )
        assert isinstance(chain, SolverChain)
        for mg in chain.machine_groups:
            assert mg.clock_speed_pct == 100, (
                f"Expected 100% for {mg.recipe.class_name}, got {mg.clock_speed_pct}"
            )

    def test_machine_counts_unchanged(self) -> None:
        gd = _game_data()
        sel = _selection_standard_frame(gd)
        chain_on = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        chain_off = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, False, gd)
        assert isinstance(chain_on, SolverChain)
        assert isinstance(chain_off, SolverChain)
        counts_on = {mg.recipe.class_name: mg.machine_count for mg in chain_on.machine_groups}
        counts_off = {mg.recipe.class_name: mg.machine_count for mg in chain_off.machine_groups}
        assert counts_on == counts_off

    def test_exact_rates_unchanged(self) -> None:
        gd = _game_data()
        sel = _selection_standard_frame(gd)
        chain_on = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        chain_off = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, False, gd)
        assert isinstance(chain_on, SolverChain)
        assert isinstance(chain_off, SolverChain)
        for mg_c, mg_u in zip(chain_on.machine_groups, chain_off.machine_groups, strict=True):
            assert abs(mg_c.exact_recipe_rate - mg_u.exact_recipe_rate) < 1e-9


# ===========================================================================
# Bonded alternate RZP recipe — different rates and raw resources
# ===========================================================================


class TestBondedFrameRates:
    """Rates for ZorblaxFrame using Bonded (alternate) RZP recipe.

    Bonded: 18.75 Plate/min + 37.5 Sprongite/min → 5.625 RZP/min
    """

    def test_frame_recipe_rate(self) -> None:
        gd = _game_data()
        sel = _selection_bonded_frame(gd)
        chain = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        assert isinstance(chain, SolverChain)
        assert abs(_group(chain, _RECIPE_FRAME).exact_recipe_rate - 2.5) < 1e-9

    def test_bonded_rzp_recipe_rate(self) -> None:
        gd = _game_data()
        sel = _selection_bonded_frame(gd)
        chain = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        assert isinstance(chain, SolverChain)
        # demand 7.5 RZP/min; Bonded produces 5.625 RZP/min → rate = 7.5 / 5.625 = 1.333...
        expected = 7.5 / 5.625
        assert abs(_group(chain, _RECIPE_BONDED).exact_recipe_rate - expected) < 1e-9

    def test_zorblax_raw_consumption(self) -> None:
        gd = _game_data()
        sel = _selection_bonded_frame(gd)
        chain = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        assert isinstance(chain, SolverChain)
        # Plate demand from Bonded: (7.5/5.625) * 18.75 = 25.0; Plate rate = 25/20 = 1.25
        # Zorblax from Plate: 1.25 * 30 = 37.5
        # Zorblax from Rod: (2.5*12/15) * 15 = 30.0
        assert abs(chain.raw_resource_consumption[_ZORBLAX] - 67.5) < 1e-6

    def test_sprongite_raw_consumption(self) -> None:
        gd = _game_data()
        sel = _selection_bonded_frame(gd)
        chain = calculate_quantities(sel, {_FRAME: TARGET_FRAME}, True, gd)
        assert isinstance(chain, SolverChain)
        # Bonded rate = 7.5/5.625 ≈ 1.3333; Sprongite demand = 1.3333 * 37.5 = 50.0
        assert abs(chain.raw_resource_consumption[_SPRONGITE] - 50.0) < 1e-6


# ===========================================================================
# Cyclic chain — numpy solver, net zero input
# ===========================================================================


class TestCyclicAquaChain:
    """AquaCycle: 6 Aqua/min → 6 Solid/min + 6 Aqua/min (cycle).

    At steady state the chain is self-sustaining for AquaZorblax.
    """

    def test_recipe_rate(self) -> None:
        gd = _cyclic_game_data()
        sel = _selection_cyclic(gd)
        chain = calculate_quantities(sel, {_SOLID: 12.0}, True, gd)
        assert isinstance(chain, SolverChain)
        # 12 Solid/min ÷ 6 Solid per machine = 2.0
        assert abs(_group(chain, _RECIPE_AQUA).exact_recipe_rate - 2.0) < 1e-9

    def test_machine_count(self) -> None:
        gd = _cyclic_game_data()
        sel = _selection_cyclic(gd)
        chain = calculate_quantities(sel, {_SOLID: 12.0}, True, gd)
        assert isinstance(chain, SolverChain)
        assert _group(chain, _RECIPE_AQUA).machine_count == 2

    def test_clock_speed(self) -> None:
        gd = _cyclic_game_data()
        sel = _selection_cyclic(gd)
        chain = calculate_quantities(sel, {_SOLID: 12.0}, True, gd)
        assert isinstance(chain, SolverChain)
        # rate 2.0 / count 2 = exactly 100%
        assert _group(chain, _RECIPE_AQUA).clock_speed_pct == 100

    def test_net_aqua_input_is_zero(self) -> None:
        """The cycle is self-sustaining: no external AquaZorblax input required."""
        gd = _cyclic_game_data()
        sel = _selection_cyclic(gd)
        chain = calculate_quantities(sel, {_SOLID: 12.0}, True, gd)
        assert isinstance(chain, SolverChain)
        # AquaZorblax is produced and consumed at equal rates — net input = 0.
        assert _AQUA not in chain.raw_resource_consumption

    def test_no_implicit_outputs(self) -> None:
        gd = _cyclic_game_data()
        sel = _selection_cyclic(gd)
        chain = calculate_quantities(sel, {_SOLID: 12.0}, True, gd)
        assert isinstance(chain, SolverChain)
        # AquaZorblax net = 0, so it is not surfaced as an implicit output.
        assert chain.implicit_outputs == {}

    def test_is_cycle_flagged(self) -> None:
        gd = _cyclic_game_data()
        sel = _selection_cyclic(gd)
        chain = calculate_quantities(sel, {_SOLID: 12.0}, True, gd)
        assert isinstance(chain, SolverChain)
        assert chain.has_cycle


# ===========================================================================
# Implicit outputs (byproducts not declared as desired outputs)
# ===========================================================================


class TestImplicitOutputs:
    """A recipe that produces an extra item the chain does not consume."""

    def test_byproduct_is_implicit_output(self) -> None:
        # Recipe: 10 Raw/min → 5 MainItem/min + 3 Byproduct/min
        recipe = _make_recipe(
            "R_Main",
            ingredients=[("Desc_Raw_C", 10.0)],
            products=[("Desc_Main_C", 5.0), ("Desc_By_C", 3.0)],
        )
        gd = _make_game_data([recipe], raw_items=["Desc_Raw_C"])
        sel = RecipeSelection(recipes={"R_Main": recipe}, has_cycle=False)

        chain = calculate_quantities(sel, {"Desc_Main_C": 10.0}, True, gd)
        assert isinstance(chain, SolverChain)
        # rate = 10.0 / 5.0 = 2.0 → Byproduct = 2.0 * 3.0 = 6.0/min
        assert abs(chain.implicit_outputs.get("Desc_By_C", 0.0) - 6.0) < 1e-9

    def test_desired_item_not_in_implicit_outputs(self) -> None:
        recipe = _make_recipe(
            "R_Main",
            ingredients=[("Desc_Raw_C", 10.0)],
            products=[("Desc_Main_C", 5.0), ("Desc_By_C", 3.0)],
        )
        gd = _make_game_data([recipe], raw_items=["Desc_Raw_C"])
        sel = RecipeSelection(recipes={"R_Main": recipe}, has_cycle=False)

        chain = calculate_quantities(sel, {"Desc_Main_C": 10.0}, True, gd)
        assert isinstance(chain, SolverChain)
        assert "Desc_Main_C" not in chain.implicit_outputs

    def test_raw_resource_consumption_with_byproduct_recipe(self) -> None:
        recipe = _make_recipe(
            "R_Main",
            ingredients=[("Desc_Raw_C", 10.0)],
            products=[("Desc_Main_C", 5.0), ("Desc_By_C", 3.0)],
        )
        gd = _make_game_data([recipe], raw_items=["Desc_Raw_C"])
        sel = RecipeSelection(recipes={"R_Main": recipe}, has_cycle=False)

        chain = calculate_quantities(sel, {"Desc_Main_C": 10.0}, True, gd)
        assert isinstance(chain, SolverChain)
        # rate 2.0 consumes 2.0 * 10.0 = 20.0 Raw/min
        assert abs(chain.raw_resource_consumption.get("Desc_Raw_C", 0.0) - 20.0) < 1e-9

    def test_byproduct_consumed_within_chain_not_surfaced(self) -> None:
        # Recipe A: Raw → X + Y; Recipe B: Y → Z (desired).
        # A was added specifically to supply Y to B (no byproduct routing — byproduct_deps
        # is empty).  Y is fully consumed so it must NOT appear as an implicit output.
        # X is the true surplus and should appear as an implicit output.
        recipe_a = _make_recipe(
            "R_A",
            ingredients=[("Desc_Raw_C", 6.0)],
            products=[("Desc_X_C", 3.0), ("Desc_Y_C", 6.0)],
        )
        recipe_b = _make_recipe(
            "R_B",
            ingredients=[("Desc_Y_C", 6.0)],
            products=[("Desc_Z_C", 2.0)],
        )
        gd = _make_game_data([recipe_a, recipe_b], raw_items=["Desc_Raw_C"])
        # No byproduct routing: A was selected explicitly to produce Y.
        sel = RecipeSelection(
            recipes={"R_A": recipe_a, "R_B": recipe_b},
            has_cycle=False,
        )
        # Target: 2 Z/min → R_B rate = 1.0 → consumes 6 Y/min
        # R_A rate = 1.0 to produce 6 Y/min (and 3 X/min surplus)
        chain = calculate_quantities(sel, {"Desc_Z_C": 2.0}, True, gd)
        assert isinstance(chain, SolverChain)
        assert "Desc_Y_C" not in chain.implicit_outputs
        # X is a surplus — should appear as implicit output
        assert abs(chain.implicit_outputs.get("Desc_X_C", 0.0) - 3.0) < 1e-9


# ===========================================================================
# Phase 2 failure: non-raw deficit
# ===========================================================================


class TestPhase2Failure:
    """Phase2Failure is returned when a non-raw intermediate has a net deficit."""

    def test_returns_phase2_failure_for_non_raw_deficit(self) -> None:
        # Recipe A: Raw → 1 X/min + 1 Y/min (byproduct)
        # Recipe B: Y → Z (needs 2 Y/min, but A only produces 1 Y/min at the rate needed for X)
        recipe_a = _make_recipe(
            "R_A",
            ingredients=[("Desc_Raw_C", 10.0)],
            products=[("Desc_X_C", 2.0), ("Desc_Y_C", 1.0)],
        )
        recipe_b = _make_recipe(
            "R_B",
            ingredients=[("Desc_Y_C", 2.0)],
            products=[("Desc_Z_C", 1.0)],
        )
        gd = _make_game_data([recipe_a, recipe_b], raw_items=["Desc_Raw_C"])
        # target: 2 X/min (rate A=1.0) AND 2 Z/min (rate B=2.0 → needs 4 Y/min)
        # A at rate 1.0 only produces 1 Y/min, but B needs 4 Y/min — deficit!
        sel = RecipeSelection(
            recipes={"R_A": recipe_a, "R_B": recipe_b},
            has_cycle=False,
            byproduct_deps={"Desc_Y_C": "R_A"},
        )
        result = calculate_quantities(sel, {"Desc_X_C": 2.0, "Desc_Z_C": 2.0}, True, gd)
        assert isinstance(result, Phase2Failure)
        assert result.item_class == "Desc_Y_C"


# ===========================================================================
# Empty / degenerate inputs
# ===========================================================================


class TestDegenerateConverterCycle:
    """Cyclic converter chains that produce negative lstsq rates must be rejected."""

    def test_converter_cycle_returns_phase2_failure(self) -> None:
        """A → B → C → A converter cycle has no non-negative solution and must fail."""
        # A→B, B→C, C→A form a pure cycle.  With a desired output of D produced
        # by another recipe that also needs A, lstsq can give negative rates.
        recipe_a_to_b = _make_recipe("R_AB", [("Desc_A_C", 10.0)], [("Desc_B_C", 10.0)])
        recipe_b_to_c = _make_recipe("R_BC", [("Desc_B_C", 10.0)], [("Desc_C_C", 10.0)])
        recipe_c_to_a = _make_recipe("R_CA", [("Desc_C_C", 10.0)], [("Desc_A_C", 10.0)])
        recipe_a_to_d = _make_recipe("R_AD", [("Desc_A_C", 10.0)], [("Desc_D_C", 10.0)])
        gd = _make_game_data(
            [recipe_a_to_b, recipe_b_to_c, recipe_c_to_a, recipe_a_to_d],
            raw_items=[],
        )
        sel = RecipeSelection(
            recipes={
                "R_AB": recipe_a_to_b,
                "R_BC": recipe_b_to_c,
                "R_CA": recipe_c_to_a,
                "R_AD": recipe_a_to_d,
            },
            has_cycle=True,
        )
        result = calculate_quantities(sel, {"Desc_D_C": 10.0}, True, gd)
        assert isinstance(result, Phase2Failure)


class TestEdgeCases:
    def test_empty_selection_returns_empty_chain(self) -> None:
        gd = _game_data()
        sel = RecipeSelection(recipes={}, has_cycle=False)
        chain = calculate_quantities(sel, {}, True, gd)
        assert isinstance(chain, SolverChain)
        assert chain.machine_groups == []
        assert chain.raw_resource_consumption == {}
        assert chain.implicit_outputs == {}

    def test_single_recipe_exact_rate(self) -> None:
        """One machine at exactly 100% — count 1, clock 100%."""
        recipe = _make_recipe(
            "R_Single",
            ingredients=[("Desc_Raw_C", 10.0)],
            products=[("Desc_Out_C", 10.0)],
        )
        gd = _make_game_data([recipe], raw_items=["Desc_Raw_C"])
        sel = RecipeSelection(recipes={"R_Single": recipe}, has_cycle=False)
        chain = calculate_quantities(sel, {"Desc_Out_C": 10.0}, True, gd)
        assert isinstance(chain, SolverChain)
        mg = chain.machine_groups[0]
        assert mg.machine_count == 1
        assert mg.clock_speed_pct == 100
        assert abs(mg.exact_recipe_rate - 1.0) < 1e-9


# ===========================================================================
# Fixtures / helpers
# ===========================================================================


def _group(chain: SolverChain, recipe_class: str) -> MachineGroup:
    """Return the MachineGroup for the given recipe, failing clearly if absent."""
    for mg in chain.machine_groups:
        if mg.recipe.class_name == recipe_class:
            return mg
    names = [mg.recipe.class_name for mg in chain.machine_groups]
    raise AssertionError(f"No MachineGroup for {recipe_class!r}. Present: {names}")


def _make_recipe(
    class_name: str,
    ingredients: list[tuple[str, float]],
    products: list[tuple[str, float]],
) -> Recipe:
    """Build a Recipe from simple (item_class, amount_per_min) tuples."""
    return Recipe(
        class_name=class_name,
        display_name=class_name,
        machine_class="Build_Test_C",
        ingredients=[ItemAmount(ic, amt) for ic, amt in ingredients],
        products=[ItemAmount(ic, amt) for ic, amt in products],
        duration=60.0,
    )


def _make_game_data(recipes: list[Recipe], raw_items: list[str]) -> GameData:
    """Minimal GameData with the given recipes and declared raw items."""
    all_items: set[str] = set(raw_items)
    for r in recipes:
        for p in r.products:
            all_items.add(p.item_class)
        for ing in r.ingredients:
            all_items.add(ing.item_class)
    return GameData(
        items={ic: Item(ic, ic) for ic in all_items},
        machines={},
        recipes=recipes,
    )
