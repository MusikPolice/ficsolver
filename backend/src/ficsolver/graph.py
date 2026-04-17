"""Bipartite directed graph of items and production recipes.

Node keys:
  "item:{class_name}"    — node_type="item"
  "recipe:{class_name}"  — node_type="recipe"

Edges:
  item → recipe   (ingredient; weight = amount_per_min)
  recipe → item   (product;    weight = amount_per_min)

Build-gun recipes are excluded.
"""

from __future__ import annotations

import networkx as nx

from ficsolver.models import GameData


def build_recipe_graph(game_data: GameData) -> nx.DiGraph:
    g: nx.DiGraph = nx.DiGraph()

    for class_name, item in game_data.items.items():
        g.add_node(
            f"item:{class_name}",
            node_type="item",
            class_name=class_name,
            display_name=item.display_name,
        )

    for recipe in game_data.recipes:
        if recipe.is_build_gun:
            continue

        rnode = f"recipe:{recipe.class_name}"
        g.add_node(
            rnode,
            node_type="recipe",
            class_name=recipe.class_name,
            display_name=recipe.display_name,
            machine_class=recipe.machine_class,
            is_alternate=recipe.is_alternate,
        )

        for ingredient in recipe.ingredients:
            inode = f"item:{ingredient.item_class}"
            if inode not in g:
                g.add_node(
                    inode,
                    node_type="item",
                    class_name=ingredient.item_class,
                    display_name=ingredient.item_class,
                )
            g.add_edge(inode, rnode, amount_per_min=ingredient.amount_per_min)

        for product in recipe.products:
            inode = f"item:{product.item_class}"
            if inode not in g:
                g.add_node(
                    inode,
                    node_type="item",
                    class_name=product.item_class,
                    display_name=product.item_class,
                )
            g.add_edge(rnode, inode, amount_per_min=product.amount_per_min)

    return g
