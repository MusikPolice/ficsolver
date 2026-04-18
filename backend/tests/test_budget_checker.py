"""Budget checker tests: resource consumption compared against available inputs.

Uses the Zorblax fixture universe. All rates are per minute.

Standard ZorblaxFrame chain for 5 Frame/min consumes 63.75 Zorblax/min total:
  Rod recipe (2.0 runs): 2.0 * 15.0 = 30.0 Zorblax/min
  Plate recipe (1.125 runs): 1.125 * 30.0 = 33.75 Zorblax/min

Bonded ZorblaxFrame chain also consumes Sprongite (second raw resource), used to
test multi-resource budget comparison. Exact values are derived from Phase 2 and
asserted via approximate equality (1e-6).
"""

from ficsolver.models import BudgetComparison, SolverChain
from ficsolver.parser import parse_game_data
from ficsolver.solver import calculate_quantities, check_budget, select_recipes
from tests.fixtures.game_data import FIXTURE

_FRAME = "Desc_ZorblaxFrame_C"
_ZORBLAX = "Desc_Zorblax_C"
_SPRONGITE = "Desc_Sprongite_C"
_RECIPE_BONDED = "Recipe_Alternate_BondedZorblaxPlate_C"

TARGET_FRAME = 5.0
# Standard chain consumes exactly 63.75 Zorblax/min for 5 Frame/min.
STANDARD_ZORBLAX_CONSUMED = 63.75


def _standard_chain() -> SolverChain:
    gd = parse_game_data(FIXTURE)
    result = select_recipes([_FRAME], set(), gd)
    chain = calculate_quantities(result.selections[0], {_FRAME: TARGET_FRAME}, True, gd)
    assert isinstance(chain, SolverChain)
    return chain


def _bonded_chain() -> SolverChain:
    gd = parse_game_data(FIXTURE)
    result = select_recipes([_FRAME], {_RECIPE_BONDED}, gd)
    bonded = [s for s in result.selections if _RECIPE_BONDED in s.recipes]
    assert bonded
    chain = calculate_quantities(bonded[0], {_FRAME: TARGET_FRAME}, True, gd)
    assert isinstance(chain, SolverChain)
    return chain


# ===========================================================================
# Deficit case -- mirrors Modular Frame -108 Iron Ingot example from spec
# ===========================================================================


class TestDeficitCase:
    """Available inputs are less than what the chain requires."""

    def test_has_deficit_true(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: 50.0})
        assert result.has_deficit is True

    def test_deficit_entry_present(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: 50.0})
        assert _ZORBLAX in result.entries

    def test_deficit_delta_correct(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: 50.0})
        entry = result.entries[_ZORBLAX]
        # delta = 50.0 - 63.75 = -13.75
        assert abs(entry.delta - (50.0 - STANDARD_ZORBLAX_CONSUMED)) < 1e-6

    def test_deficit_available_correct(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: 50.0})
        assert abs(result.entries[_ZORBLAX].available - 50.0) < 1e-6

    def test_deficit_consumed_correct(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: 50.0})
        assert abs(result.entries[_ZORBLAX].consumed - STANDARD_ZORBLAX_CONSUMED) < 1e-6

    def test_returns_budget_comparison(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: 50.0})
        assert isinstance(result, BudgetComparison)


# ===========================================================================
# Surplus case
# ===========================================================================


class TestSurplusCase:
    """Available inputs exceed what the chain requires."""

    def test_has_deficit_false(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: 80.0})
        assert result.has_deficit is False

    def test_surplus_delta_correct(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: 80.0})
        entry = result.entries[_ZORBLAX]
        # delta = 80.0 - 63.75 = 16.25
        assert abs(entry.delta - (80.0 - STANDARD_ZORBLAX_CONSUMED)) < 1e-6

    def test_surplus_available_correct(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: 80.0})
        assert abs(result.entries[_ZORBLAX].available - 80.0) < 1e-6


# ===========================================================================
# Exact match — delta is zero
# ===========================================================================


class TestExactMatch:
    def test_zero_delta(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: STANDARD_ZORBLAX_CONSUMED})
        assert abs(result.entries[_ZORBLAX].delta) < 1e-6

    def test_has_deficit_false_on_exact(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: STANDARD_ZORBLAX_CONSUMED})
        assert result.has_deficit is False


# ===========================================================================
# Undeclared resource consumed by chain
# ===========================================================================


class TestUndeclaredResource:
    """Chain consumes a resource the user did not declare in available_inputs."""

    def test_undeclared_resource_available_is_zero(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {})  # no inputs declared
        assert abs(result.entries[_ZORBLAX].available) < 1e-6

    def test_undeclared_resource_has_deficit(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {})
        assert result.has_deficit is True

    def test_undeclared_resource_delta_equals_negative_consumed(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {})
        entry = result.entries[_ZORBLAX]
        assert abs(entry.delta - (-STANDARD_ZORBLAX_CONSUMED)) < 1e-6


# ===========================================================================
# Declared input not consumed by chain
# ===========================================================================


class TestDeclaredButUnconsumed:
    """User declares an input that this chain does not consume."""

    def test_extra_resource_included_in_entries(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: 80.0, _SPRONGITE: 100.0})
        assert _SPRONGITE in result.entries

    def test_extra_resource_consumed_is_zero(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: 80.0, _SPRONGITE: 100.0})
        assert abs(result.entries[_SPRONGITE].consumed) < 1e-6

    def test_extra_resource_delta_equals_available(self) -> None:
        chain = _standard_chain()
        result = check_budget(chain, {_ZORBLAX: 80.0, _SPRONGITE: 100.0})
        assert abs(result.entries[_SPRONGITE].delta - 100.0) < 1e-6


# ===========================================================================
# Multi-resource chain (Bonded RZP uses Sprongite)
# ===========================================================================


class TestMultiResourceChain:
    """Bonded chain consumes both Zorblax and Sprongite."""

    def test_both_resources_in_entries(self) -> None:
        chain = _bonded_chain()
        result = check_budget(chain, {_ZORBLAX: 100.0, _SPRONGITE: 100.0})
        assert _ZORBLAX in result.entries
        assert _SPRONGITE in result.entries

    def test_sprongite_consumed_is_positive(self) -> None:
        chain = _bonded_chain()
        result = check_budget(chain, {_ZORBLAX: 100.0, _SPRONGITE: 100.0})
        assert result.entries[_SPRONGITE].consumed > 0

    def test_deficit_on_insufficient_sprongite(self) -> None:
        chain = _bonded_chain()
        sprongite_consumed = chain.raw_resource_consumption.get(_SPRONGITE, 0.0)
        result = check_budget(chain, {_ZORBLAX: 200.0, _SPRONGITE: sprongite_consumed - 1.0})
        assert result.has_deficit is True

    def test_no_deficit_on_sufficient_inputs(self) -> None:
        chain = _bonded_chain()
        zorblax = chain.raw_resource_consumption.get(_ZORBLAX, 0.0)
        sprongite = chain.raw_resource_consumption.get(_SPRONGITE, 0.0)
        result = check_budget(chain, {_ZORBLAX: zorblax + 10.0, _SPRONGITE: sprongite + 10.0})
        assert result.has_deficit is False

    def test_item_class_field_matches_key(self) -> None:
        chain = _bonded_chain()
        result = check_budget(chain, {_ZORBLAX: 100.0, _SPRONGITE: 100.0})
        for key, entry in result.entries.items():
            assert entry.item_class == key
