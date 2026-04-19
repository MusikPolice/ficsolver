"""Integration tests for GET /items and GET /recipes endpoints."""

import pytest
from fastapi.testclient import TestClient

from ficsolver.main import app, get_game_data
from ficsolver.parser import parse_game_data
from tests.fixtures.game_data import FIXTURE


@pytest.fixture
def client() -> TestClient:
    game_data = parse_game_data(FIXTURE)
    app.dependency_overrides[get_game_data] = lambda: game_data
    yield TestClient(app)  # type: ignore[misc]
    app.dependency_overrides.clear()


def test_list_items_status(client: TestClient) -> None:
    assert client.get("/items").status_code == 200


def test_list_items_count(client: TestClient) -> None:
    items = client.get("/items").json()
    # 7 FGItemDescriptor + 1 FGResourceDescriptor; FGBuildingDescriptor excluded (no display name)
    assert len(items) == 8


def test_list_items_excludes_unnamed(client: TestClient) -> None:
    items = client.get("/items").json()
    # Building descriptors (e.g. Desc_Beam_C) have no mDisplayName and must be filtered out
    assert all(i["display_name"] for i in items)


def test_list_items_sorted_alphabetically(client: TestClient) -> None:
    items = client.get("/items").json()
    names = [i["display_name"] for i in items]
    assert names == sorted(names)


def test_list_items_shape(client: TestClient) -> None:
    items = client.get("/items").json()
    rod = next(i for i in items if i["class_name"] == "Desc_ZorblaxRod_C")
    assert rod["display_name"] == "Zorblax Rod"
    assert set(rod.keys()) == {"class_name", "display_name", "is_raw_resource"}


def test_list_recipes_status(client: TestClient) -> None:
    assert client.get("/recipes").status_code == 200


def test_list_recipes_count(client: TestClient) -> None:
    recipes = client.get("/recipes").json()
    assert len(recipes) == 7  # 6 production + 1 build-gun


def test_list_recipes_shape(client: TestClient) -> None:
    recipes = client.get("/recipes").json()
    rod = next(r for r in recipes if r["class_name"] == "Recipe_ZorblaxRod_C")
    assert rod["display_name"] == "Zorblax Rod"
    assert len(rod["ingredients"]) == 1
    assert len(rod["products"]) == 1
    assert rod["is_alternate"] is False
    assert rod["is_build_gun"] is False


def test_list_recipes_ingredient_shape(client: TestClient) -> None:
    recipes = client.get("/recipes").json()
    rod = next(r for r in recipes if r["class_name"] == "Recipe_ZorblaxRod_C")
    ingredient = rod["ingredients"][0]
    assert ingredient["item_class"] == "Desc_Zorblax_C"
    assert ingredient["amount_per_min"] == pytest.approx(15.0)


def test_list_recipes_includes_alternate(client: TestClient) -> None:
    recipes = client.get("/recipes").json()
    alternates = [r for r in recipes if r["is_alternate"]]
    assert len(alternates) == 2
    alt_names = {r["class_name"] for r in alternates}
    assert "Recipe_Alternate_BondedZorblaxPlate_C" in alt_names
    assert "Recipe_Alternate_ZorblaxGear_C" in alt_names


def test_list_recipes_includes_build_gun(client: TestClient) -> None:
    recipes = client.get("/recipes").json()
    build_gun_recipes = [r for r in recipes if r["is_build_gun"]]
    assert len(build_gun_recipes) == 1
    assert build_gun_recipes[0]["class_name"] == "Recipe_Build_FabricatorMk1_C"
