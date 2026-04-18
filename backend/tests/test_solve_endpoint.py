"""Integration tests for POST /solve and GET /solve/{id}/results endpoints.

Uses the Zorblax fixture universe. The standard ZorblaxFrame chain requires
only Zorblax as a raw resource (63.75/min for 5 Frame/min). The Bonded
variant also requires Sprongite, giving a different total resource consumption.

Key item / recipe class names:
  Desc_ZorblaxFrame_C                — desired output in most tests
  Desc_Zorblax_C                     — raw resource for standard chain
  Desc_Sprongite_C                   — second raw resource for bonded chain
  Recipe_Alternate_BondedZorblaxPlate_C — unlockable alternate
  Desc_ZorblaxGear_C                 — only produceable via locked alternate
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ficsolver.main import _solve_cache, app, get_game_data
from ficsolver.parser import parse_game_data
from ficsolver.solver import Phase1Result, select_recipes
from tests.fixtures.game_data import FIXTURE

_FRAME = "Desc_ZorblaxFrame_C"
_ZORBLAX = "Desc_Zorblax_C"
_SPRONGITE = "Desc_Sprongite_C"
_GEAR = "Desc_ZorblaxGear_C"
_BONDED_ALT = "Recipe_Alternate_BondedZorblaxPlate_C"

_SOLVE_URL = "/solve"
_TARGET_RATE = 5.0
_ZORBLAX_BUDGET = 100.0


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    _solve_cache.clear()


@pytest.fixture
def client() -> TestClient:
    game_data = parse_game_data(FIXTURE)
    app.dependency_overrides[get_game_data] = lambda: game_data
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()


def _post_solve(
    client: TestClient,
    outputs: dict[str, float] | None = None,
    inputs: dict[str, float] | None = None,
    unlocked_alternates: list[str] | None = None,
    clocking_available: bool = True,
    page_size: int = 10,
) -> dict:  # type: ignore[type-arg]
    body = {
        "outputs": outputs if outputs is not None else {_FRAME: _TARGET_RATE},
        "inputs": inputs if inputs is not None else {_ZORBLAX: _ZORBLAX_BUDGET},
        "unlocked_alternates": unlocked_alternates if unlocked_alternates is not None else [],
        "clocking_available": clocking_available,
        "page_size": page_size,
    }
    resp = client.post(_SOLVE_URL, json=body)
    return resp.json()  # type: ignore[no-any-return]


# ===========================================================================
# Valid request — first page + metadata
# ===========================================================================


class TestValidRequest:
    def test_status_200(self, client: TestClient) -> None:
        resp = client.post(
            _SOLVE_URL,
            json={
                "outputs": {_FRAME: _TARGET_RATE},
                "inputs": {_ZORBLAX: _ZORBLAX_BUDGET},
            },
        )
        assert resp.status_code == 200

    def test_solve_id_present(self, client: TestClient) -> None:
        data = _post_solve(client)
        assert data["solve_id"] is not None
        assert len(data["solve_id"]) == 36  # UUID4

    def test_total_count_positive(self, client: TestClient) -> None:
        data = _post_solve(client)
        assert data["total_count"] >= 1

    def test_page_is_one(self, client: TestClient) -> None:
        data = _post_solve(client)
        assert data["page"] == 1

    def test_page_size_matches_request(self, client: TestClient) -> None:
        data = _post_solve(client, page_size=5)
        assert data["page_size"] == 5

    def test_results_not_empty(self, client: TestClient) -> None:
        data = _post_solve(client)
        assert len(data["results"]) >= 1

    def test_results_capped_at_page_size(self, client: TestClient) -> None:
        data = _post_solve(client, page_size=1)
        assert len(data["results"]) <= 1

    def test_failure_is_null(self, client: TestClient) -> None:
        data = _post_solve(client)
        assert data["failure"] is None

    def test_cap_reached_false_for_small_fixture(self, client: TestClient) -> None:
        data = _post_solve(client)
        assert data["cap_reached"] is False

    def test_result_has_machine_groups(self, client: TestClient) -> None:
        data = _post_solve(client)
        chain = data["results"][0]
        assert len(chain["machine_groups"]) >= 1

    def test_result_machine_group_shape(self, client: TestClient) -> None:
        data = _post_solve(client)
        mg = data["results"][0]["machine_groups"][0]
        required = {
            "recipe_class",
            "recipe_display_name",
            "machine_class",
            "machine_count",
            "clock_speed_pct",
            "exact_recipe_rate",
        }
        assert required.issubset(mg.keys())

    def test_result_budget_present(self, client: TestClient) -> None:
        data = _post_solve(client)
        chain = data["results"][0]
        assert "budget" in chain
        assert len(chain["budget"]) >= 1

    def test_result_budget_entry_shape(self, client: TestClient) -> None:
        data = _post_solve(client)
        chain = data["results"][0]
        entry = next(iter(chain["budget"].values()))
        assert set(entry.keys()) == {"item_class", "available", "consumed", "delta"}

    def test_no_deficit_when_budget_sufficient(self, client: TestClient) -> None:
        data = _post_solve(client, inputs={_ZORBLAX: 1000.0})
        for chain in data["results"]:
            assert chain["has_deficit"] is False

    def test_all_chains_have_deficit_flag(self, client: TestClient) -> None:
        # Declare no inputs → all chains will have a deficit.
        data = _post_solve(client, inputs={})
        assert data["all_chains_have_deficit"] is True

    def test_results_sorted_ascending_by_resource(self, client: TestClient) -> None:
        data = _post_solve(client, unlocked_alternates=[_BONDED_ALT])
        totals = [c["total_resource_consumed"] for c in data["results"]]
        assert totals == sorted(totals)


# ===========================================================================
# Pagination — second page returns correct slice
# ===========================================================================


class TestPagination:
    def test_second_page_returns_next_slice(self, client: TestClient) -> None:
        # Unlock alternate to get at least 2 chains.
        data_p1 = _post_solve(client, unlocked_alternates=[_BONDED_ALT], page_size=1)
        solve_id = data_p1["solve_id"]
        total = data_p1["total_count"]
        if total < 2:
            pytest.skip("fixture produced fewer than 2 chains")

        resp2 = client.get(f"/solve/{solve_id}/results?page=2&page_size=1")
        assert resp2.status_code == 200
        data_p2 = resp2.json()
        assert data_p2["page"] == 2
        # The chains on page 1 and page 2 must be different.
        p1_total = data_p1["results"][0]["total_resource_consumed"] if data_p1["results"] else None
        p2_total = data_p2["results"][0]["total_resource_consumed"] if data_p2["results"] else None
        assert p1_total != p2_total or p1_total is None

    def test_second_page_total_count_unchanged(self, client: TestClient) -> None:
        data_p1 = _post_solve(client, unlocked_alternates=[_BONDED_ALT], page_size=1)
        solve_id = data_p1["solve_id"]
        total = data_p1["total_count"]
        resp2 = client.get(f"/solve/{solve_id}/results?page=2&page_size=1")
        assert resp2.json()["total_count"] == total

    def test_page_beyond_results_returns_empty(self, client: TestClient) -> None:
        data = _post_solve(client, page_size=100)
        solve_id = data["solve_id"]
        resp = client.get(f"/solve/{solve_id}/results?page=999&page_size=100")
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_unknown_solve_id_returns_404(self, client: TestClient) -> None:
        resp = client.get("/solve/00000000-0000-0000-0000-000000000000/results")
        assert resp.status_code == 404


# ===========================================================================
# Sort parameter
# ===========================================================================


class TestSortParam:
    def test_resource_sort_ascending(self, client: TestClient) -> None:
        data = _post_solve(client, unlocked_alternates=[_BONDED_ALT])
        solve_id = data["solve_id"]
        resp = client.get(f"/solve/{solve_id}/results?sort=resource")
        assert resp.status_code == 200
        totals = [c["total_resource_consumed"] for c in resp.json()["results"]]
        assert totals == sorted(totals)

    def test_solve_id_preserved_in_get_response(self, client: TestClient) -> None:
        data = _post_solve(client)
        solve_id = data["solve_id"]
        resp = client.get(f"/solve/{solve_id}/results?sort=resource")
        assert resp.json()["solve_id"] == solve_id


# ===========================================================================
# cap_reached flag
# ===========================================================================


class TestCapReached:
    def test_cap_reached_true_when_limit_hit(self, client: TestClient) -> None:
        game_data = parse_game_data(FIXTURE)
        app.dependency_overrides[get_game_data] = lambda: game_data

        # Build a real Phase1Result with cap_reached=True using an actual selection.
        real_result = select_recipes([_FRAME], set(), game_data)
        if not real_result.selections:
            pytest.skip("no selections in fixture")

        capped_result = Phase1Result(selections=real_result.selections, cap_reached=True)

        with patch("ficsolver.main.select_recipes", return_value=capped_result):
            data = _post_solve(client)
            assert data["cap_reached"] is True


# ===========================================================================
# Phase 1 failure
# ===========================================================================


class TestPhase1Failure:
    def test_gear_without_alternate_is_phase1_failure(self, client: TestClient) -> None:
        # ZorblaxGear has no standard recipe — requires the locked alternate.
        resp = client.post(
            _SOLVE_URL,
            json={
                "outputs": {_GEAR: 1.0},
                "inputs": {_ZORBLAX: 100.0},
                "unlocked_alternates": [],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["failure"] is not None
        assert data["failure"]["failure_type"] == "phase1"

    def test_phase1_failure_has_message(self, client: TestClient) -> None:
        resp = client.post(
            _SOLVE_URL,
            json={
                "outputs": {_GEAR: 1.0},
                "inputs": {},
                "unlocked_alternates": [],
            },
        )
        assert resp.json()["failure"]["message"]

    def test_phase1_failure_has_item_class(self, client: TestClient) -> None:
        resp = client.post(
            _SOLVE_URL,
            json={
                "outputs": {_GEAR: 1.0},
                "inputs": {},
                "unlocked_alternates": [],
            },
        )
        assert resp.json()["failure"]["item_class"] == _GEAR

    def test_phase1_failure_returns_empty_results(self, client: TestClient) -> None:
        resp = client.post(
            _SOLVE_URL,
            json={
                "outputs": {_GEAR: 1.0},
                "inputs": {},
                "unlocked_alternates": [],
            },
        )
        assert resp.json()["results"] == []

    def test_phase1_failure_no_solve_id(self, client: TestClient) -> None:
        resp = client.post(
            _SOLVE_URL,
            json={
                "outputs": {_GEAR: 1.0},
                "inputs": {},
                "unlocked_alternates": [],
            },
        )
        assert resp.json()["solve_id"] is None


# ===========================================================================
# Phase 2 failure (all chains discarded)
# ===========================================================================


class TestPhase2Failure:
    def test_all_chains_discarded_returns_phase2_failure(self, client: TestClient) -> None:
        game_data = parse_game_data(FIXTURE)
        app.dependency_overrides[get_game_data] = lambda: game_data

        with patch("ficsolver.main._solve_selection") as mock_solve:
            mock_solve.return_value = None  # all selections discarded

            resp = client.post(
                _SOLVE_URL,
                json={
                    "outputs": {_FRAME: _TARGET_RATE},
                    "inputs": {},
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["failure"] is not None
            assert data["failure"]["failure_type"] == "phase2"

    def test_phase2_failure_empty_results(self, client: TestClient) -> None:
        game_data = parse_game_data(FIXTURE)
        app.dependency_overrides[get_game_data] = lambda: game_data

        with patch("ficsolver.main._solve_selection") as mock_solve:
            mock_solve.return_value = None

            resp = client.post(
                _SOLVE_URL,
                json={
                    "outputs": {_FRAME: _TARGET_RATE},
                    "inputs": {},
                },
            )
            assert resp.json()["results"] == []


# ===========================================================================
# Unknown item validation
# ===========================================================================


class TestUnknownItem:
    def test_unknown_output_item_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            _SOLVE_URL,
            json={
                "outputs": {"Desc_Nonexistent_C": 1.0},
                "inputs": {},
            },
        )
        assert resp.status_code == 422

    def test_unknown_input_item_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            _SOLVE_URL,
            json={
                "outputs": {_FRAME: 1.0},
                "inputs": {"Desc_Nonexistent_C": 100.0},
            },
        )
        assert resp.status_code == 422

    def test_unknown_item_error_message_mentions_item(self, client: TestClient) -> None:
        resp = client.post(
            _SOLVE_URL,
            json={
                "outputs": {"Desc_Nonexistent_C": 1.0},
                "inputs": {},
            },
        )
        detail = str(resp.json())
        assert "Desc_Nonexistent_C" in detail


# ===========================================================================
# Request validation
# ===========================================================================


class TestRequestValidation:
    def test_empty_outputs_rejected(self, client: TestClient) -> None:
        resp = client.post(_SOLVE_URL, json={"outputs": {}, "inputs": {}})
        assert resp.status_code == 422

    def test_too_many_outputs_rejected(self, client: TestClient) -> None:
        outputs = {f"Desc_Item{i}_C": 1.0 for i in range(11)}
        resp = client.post(_SOLVE_URL, json={"outputs": outputs, "inputs": {}})
        # FastAPI returns 422 before any item lookup since model validation fails first.
        assert resp.status_code == 422
