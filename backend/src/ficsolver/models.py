from dataclasses import dataclass, field


@dataclass
class ItemAmount:
    """An item consumed or produced by a recipe, expressed as a per-minute rate."""

    item_class: str  # normalized short class name, e.g. "Desc_IronPlate_C"
    amount_per_min: float


@dataclass
class Item:
    """A game item (part, resource, equipment, …)."""

    class_name: str  # e.g. "Desc_IronPlate_C"
    display_name: str


@dataclass
class Machine:
    """A factory building that can execute recipes."""

    class_name: str  # e.g. "Build_ConstructorMk1_C"
    display_name: str


@dataclass
class Recipe:
    """A production recipe parsed from en-CA.json."""

    class_name: str  # e.g. "Recipe_IronPlate_C"
    display_name: str
    machine_class: str  # class_name of the primary machine
    ingredients: list[ItemAmount] = field(default_factory=list)
    products: list[ItemAmount] = field(default_factory=list)
    duration: float = 0.0  # mManufactoringDuration in seconds
    is_alternate: bool = False
    is_build_gun: bool = False


@dataclass
class GameData:
    """All parsed game data."""

    items: dict[str, Item]  # keyed by class_name
    machines: dict[str, Machine]  # keyed by class_name
    recipes: list[Recipe]
