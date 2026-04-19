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
    is_raw_resource: bool = False  # True for FGResourceDescriptor items (mineable/extractable)


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


@dataclass
class MachineGroup:
    """One group of identical machines running the same recipe."""

    recipe: Recipe
    machine_count: int
    clock_speed_pct: int  # whole-number percent, e.g. 84
    exact_recipe_rate: float  # solver solution: machines-equivalent at 100%


@dataclass
class SolverChain:
    """Phase 2 result for one RecipeSelection."""

    machine_groups: list[MachineGroup]
    raw_resource_consumption: dict[str, float]  # item_class -> rate/min consumed (positive)
    implicit_outputs: dict[str, float]  # item_class -> rate/min surplus (not declared as desired)
    has_cycle: bool


@dataclass
class ResourceBudgetEntry:
    """Budget comparison for one resource."""

    item_class: str
    available: float  # declared in user inputs (0.0 if not declared)
    consumed: float  # required by the chain
    delta: float  # available - consumed; positive = surplus, negative = deficit


@dataclass
class BudgetComparison:
    """Budget comparison for one SolverChain against the user's declared inputs."""

    entries: dict[str, ResourceBudgetEntry]  # item_class -> entry
    has_deficit: bool  # True if any delta < 0
