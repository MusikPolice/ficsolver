"""Unit tests for build_recipe_graph."""

import networkx as nx  # type: ignore[import-untyped]
import pytest

from ficsolver.graph import build_recipe_graph
from ficsolver.parser import parse_game_data
from tests.fixtures.game_data import CYCLIC_FIXTURE, FIXTURE


@pytest.fixture
def game_data():  # type: ignore[no-untyped-def]
    return parse_game_data(FIXTURE)


@pytest.fixture
def cyclic_game_data():  # type: ignore[no-untyped-def]
    return parse_game_data(CYCLIC_FIXTURE)


def test_item_node_count(game_data) -> None:  # type: ignore[no-untyped-def]
    g = build_recipe_graph(game_data)
    item_nodes = [n for n, d in g.nodes(data=True) if d["node_type"] == "item"]
    assert len(item_nodes) == 8  # 7 FGItemDescriptor + 1 FGResourceDescriptor


def test_recipe_node_count(game_data) -> None:  # type: ignore[no-untyped-def]
    g = build_recipe_graph(game_data)
    recipe_nodes = [n for n, d in g.nodes(data=True) if d["node_type"] == "recipe"]
    assert len(recipe_nodes) == 6  # 6 production recipes; build-gun excluded


def test_build_gun_excluded(game_data) -> None:  # type: ignore[no-untyped-def]
    g = build_recipe_graph(game_data)
    assert "recipe:Recipe_Build_FabricatorMk1_C" not in g


def test_ingredient_edge_present(game_data) -> None:  # type: ignore[no-untyped-def]
    g = build_recipe_graph(game_data)
    assert g.has_edge("item:Desc_Zorblax_C", "recipe:Recipe_ZorblaxRod_C")


def test_product_edge_present(game_data) -> None:  # type: ignore[no-untyped-def]
    g = build_recipe_graph(game_data)
    assert g.has_edge("recipe:Recipe_ZorblaxRod_C", "item:Desc_ZorblaxRod_C")


def test_ingredient_edge_weight(game_data) -> None:  # type: ignore[no-untyped-def]
    g = build_recipe_graph(game_data)
    edge = g["item:Desc_Zorblax_C"]["recipe:Recipe_ZorblaxRod_C"]
    assert edge["amount_per_min"] == pytest.approx(15.0)


def test_product_edge_weight(game_data) -> None:  # type: ignore[no-untyped-def]
    g = build_recipe_graph(game_data)
    edge = g["recipe:Recipe_ZorblaxRod_C"]["item:Desc_ZorblaxRod_C"]
    assert edge["amount_per_min"] == pytest.approx(15.0)


def test_multi_ingredient_edges(game_data) -> None:  # type: ignore[no-untyped-def]
    g = build_recipe_graph(game_data)
    assert g.has_edge("item:Desc_ReinforcedZorblaxPlate_C", "recipe:Recipe_ZorblaxFrame_C")
    assert g.has_edge("item:Desc_ZorblaxRod_C", "recipe:Recipe_ZorblaxFrame_C")
    assert g.has_edge("recipe:Recipe_ZorblaxFrame_C", "item:Desc_ZorblaxFrame_C")


def test_alternate_recipe_node_flagged(game_data) -> None:  # type: ignore[no-untyped-def]
    g = build_recipe_graph(game_data)
    assert "recipe:Recipe_Alternate_BondedZorblaxPlate_C" in g
    assert g.nodes["recipe:Recipe_Alternate_BondedZorblaxPlate_C"]["is_alternate"] is True


def test_acyclic_fixture_is_dag(game_data) -> None:  # type: ignore[no-untyped-def]
    g = build_recipe_graph(game_data)
    assert nx.is_directed_acyclic_graph(g)


def test_cyclic_fixture_is_not_dag(cyclic_game_data) -> None:  # type: ignore[no-untyped-def]
    g = build_recipe_graph(cyclic_game_data)
    assert not nx.is_directed_acyclic_graph(g)
