import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI

from ficsolver.models import GameData, Item, Recipe
from ficsolver.parser import load_game_data

app = FastAPI(title="ficsolver")

_GAME_DATA_PATH = Path(os.getenv("GAME_DATA_PATH", "/data/game/en-CA.json"))


@lru_cache(maxsize=1)
def get_game_data() -> GameData:
    return load_game_data(_GAME_DATA_PATH)


GameDataDep = Annotated[GameData, Depends(get_game_data)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/items")
def list_items(game_data: GameDataDep) -> list[Item]:
    return list(game_data.items.values())


@app.get("/recipes")
def list_recipes(game_data: GameDataDep) -> list[Recipe]:
    return game_data.recipes
