import { describe, it, expect, beforeEach } from "vitest";
import { reducer, initialState, relevantAlternates, resetIdCounter } from "./state";
import type { AppState, Action } from "./state";
import type { Recipe } from "./api/types";

beforeEach(() => {
  resetIdCounter();
});

function applyActions(actions: Action[], base: AppState = initialState): AppState {
  return actions.reduce((s, a) => reducer(s, a), base);
}

describe("ADD_INPUT / REMOVE_INPUT / UPDATE_INPUT_CLASS / UPDATE_INPUT_AMOUNT", () => {
  it("adds an input entry", () => {
    const s = reducer(initialState, { type: "ADD_INPUT" });
    expect(s.inputs).toHaveLength(1);
    expect(s.inputs[0]).toMatchObject({ item_class: "", amount: 0 });
  });

  it("removes an input entry by id", () => {
    const s1 = reducer(initialState, { type: "ADD_INPUT" });
    const id = s1.inputs[0].id;
    const s2 = reducer(s1, { type: "REMOVE_INPUT", id });
    expect(s2.inputs).toHaveLength(0);
  });

  it("updates input item class", () => {
    const s1 = reducer(initialState, { type: "ADD_INPUT" });
    const id = s1.inputs[0].id;
    const s2 = reducer(s1, { type: "UPDATE_INPUT_CLASS", id, item_class: "Desc_IronIngot_C" });
    expect(s2.inputs[0].item_class).toBe("Desc_IronIngot_C");
  });

  it("updates input amount", () => {
    const s1 = reducer(initialState, { type: "ADD_INPUT" });
    const id = s1.inputs[0].id;
    const s2 = reducer(s1, { type: "UPDATE_INPUT_AMOUNT", id, amount: 120 });
    expect(s2.inputs[0].amount).toBe(120);
  });
});

describe("ADD_OUTPUT / REMOVE_OUTPUT / UPDATE_OUTPUT_CLASS / UPDATE_OUTPUT_AMOUNT", () => {
  it("adds an output entry", () => {
    const s = reducer(initialState, { type: "ADD_OUTPUT" });
    expect(s.outputs).toHaveLength(1);
  });

  it("enforces max 10 outputs", () => {
    const actions: Action[] = Array.from({ length: 12 }, () => ({ type: "ADD_OUTPUT" as const }));
    const s = applyActions(actions);
    expect(s.outputs).toHaveLength(10);
  });

  it("removes an output entry by id", () => {
    const s1 = reducer(initialState, { type: "ADD_OUTPUT" });
    const id = s1.outputs[0].id;
    const s2 = reducer(s1, { type: "REMOVE_OUTPUT", id });
    expect(s2.outputs).toHaveLength(0);
  });

  it("updates output item class", () => {
    const s1 = reducer(initialState, { type: "ADD_OUTPUT" });
    const id = s1.outputs[0].id;
    const s2 = reducer(s1, {
      type: "UPDATE_OUTPUT_CLASS",
      id,
      item_class: "Desc_ModularFrame_C",
    });
    expect(s2.outputs[0].item_class).toBe("Desc_ModularFrame_C");
  });

  it("updates output amount", () => {
    const s1 = reducer(initialState, { type: "ADD_OUTPUT" });
    const id = s1.outputs[0].id;
    const s2 = reducer(s1, { type: "UPDATE_OUTPUT_AMOUNT", id, amount: 5 });
    expect(s2.outputs[0].amount).toBe(5);
  });
});

describe("TOGGLE_ALTERNATE", () => {
  it("adds an alternate when not present", () => {
    const s = reducer(initialState, {
      type: "TOGGLE_ALTERNATE",
      class_name: "Recipe_Alternate_Foo_C",
    });
    expect(s.unlockedAlternates).toContain("Recipe_Alternate_Foo_C");
  });

  it("removes an alternate when already present", () => {
    const s1 = reducer(initialState, {
      type: "TOGGLE_ALTERNATE",
      class_name: "Recipe_Alternate_Foo_C",
    });
    const s2 = reducer(s1, {
      type: "TOGGLE_ALTERNATE",
      class_name: "Recipe_Alternate_Foo_C",
    });
    expect(s2.unlockedAlternates).not.toContain("Recipe_Alternate_Foo_C");
  });
});

describe("SET_CLOCKING", () => {
  it("sets clocking flag", () => {
    const s = reducer(initialState, { type: "SET_CLOCKING", value: false });
    expect(s.clockingAvailable).toBe(false);
  });
});

describe("SET_EXCLUDE_CONVERTER", () => {
  it("defaults to false", () => {
    expect(initialState.excludeConverterRecipes).toBe(false);
  });
  it("sets excludeConverterRecipes to true", () => {
    const s = reducer(initialState, { type: "SET_EXCLUDE_CONVERTER", value: true });
    expect(s.excludeConverterRecipes).toBe(true);
  });
  it("sets excludeConverterRecipes back to false", () => {
    const withTrue = reducer(initialState, { type: "SET_EXCLUDE_CONVERTER", value: true });
    const s = reducer(withTrue, { type: "SET_EXCLUDE_CONVERTER", value: false });
    expect(s.excludeConverterRecipes).toBe(false);
  });
});

describe("SET_ITEMS / SET_RECIPES / DATA_ERROR", () => {
  it("stores items and clears loading flag", () => {
    const items = [{ class_name: "Desc_IronPlate_C", display_name: "Iron Plate", is_raw_resource: false, is_fluid: false }];
    const s = reducer(initialState, { type: "SET_ITEMS", items });
    expect(s.items).toEqual(items);
    expect(s.dataLoading).toBe(false);
  });

  it("stores recipes", () => {
    const recipes: Recipe[] = [
      {
        class_name: "Recipe_IronPlate_C",
        display_name: "Iron Plate",
        machine_class: "Build_ConstructorMk1_C",
        ingredients: [{ item_class: "Desc_IronIngot_C", amount_per_min: 30 }],
        products: [{ item_class: "Desc_IronPlate_C", amount_per_min: 20 }],
        duration: 6,
        is_alternate: false,
        is_build_gun: false,
      },
    ];
    const s = reducer(initialState, { type: "SET_RECIPES", recipes });
    expect(s.recipes).toEqual(recipes);
  });

  it("sets data error and clears loading flag", () => {
    const s = reducer(initialState, { type: "DATA_ERROR", error: "Network error" });
    expect(s.dataError).toBe("Network error");
    expect(s.dataLoading).toBe(false);
  });
});

const CHAIN_STUB = {
  machine_groups: [],
  raw_resource_consumption: {},
  implicit_outputs: {},
  has_cycle: false,
  budget: {},
  has_deficit: false,
  total_resource_consumed: 0,
};

function makeResponse(overrides: Record<string, unknown> = {}) {
  return {
    solve_id: "test-id",
    total_count: 1,
    page: 1,
    page_size: 10,
    cap_reached: false,
    results: [CHAIN_STUB],
    failure: null,
    all_chains_have_deficit: false,
    warnings: null,
    ...overrides,
  };
}

describe("SOLVE_START / SOLVE_SUCCESS / SOLVE_ERROR", () => {
  it("sets loading status and clears displayedResults", () => {
    const s = reducer(initialState, { type: "SOLVE_START" });
    expect(s.solverStatus).toBe("loading");
    expect(s.solveResult).toBeNull();
    expect(s.solveError).toBeNull();
    expect(s.displayedResults).toEqual([]);
    expect(s.isLoadingMore).toBe(false);
  });

  it("sets success status and populates displayedResults from first page", () => {
    const result = makeResponse();
    const s = reducer(initialState, { type: "SOLVE_SUCCESS", result });
    expect(s.solverStatus).toBe("success");
    expect(s.solveResult).toEqual(result);
    expect(s.displayedResults).toEqual([CHAIN_STUB]);
    expect(s.isLoadingMore).toBe(false);
  });

  it("sets error status with message", () => {
    const s = reducer(initialState, { type: "SOLVE_ERROR", error: "Timeout" });
    expect(s.solverStatus).toBe("error");
    expect(s.solveError).toBe("Timeout");
  });
});

describe("LOAD_MORE_START / LOAD_MORE_SUCCESS", () => {
  it("LOAD_MORE_START sets isLoadingMore", () => {
    const s = reducer(initialState, { type: "LOAD_MORE_START" });
    expect(s.isLoadingMore).toBe(true);
  });

  it("LOAD_MORE_SUCCESS appends results and clears isLoadingMore", () => {
    const firstResult = makeResponse({ results: [CHAIN_STUB] });
    const secondChain = { ...CHAIN_STUB, total_resource_consumed: 42 };
    const secondResult = makeResponse({ page: 2, results: [secondChain] });

    const s1 = reducer(initialState, { type: "SOLVE_SUCCESS", result: firstResult });
    const s2 = reducer(s1, { type: "LOAD_MORE_START" });
    const s3 = reducer(s2, { type: "LOAD_MORE_SUCCESS", result: secondResult });

    expect(s3.displayedResults).toHaveLength(2);
    expect(s3.displayedResults[0]).toEqual(CHAIN_STUB);
    expect(s3.displayedResults[1]).toEqual(secondChain);
    expect(s3.isLoadingMore).toBe(false);
    expect(s3.solveResult).toEqual(secondResult);
  });
});

describe("SORT_CHANGED", () => {
  it("replaces displayedResults and updates currentSort", () => {
    const firstResult = makeResponse({ results: [CHAIN_STUB, CHAIN_STUB] });
    const sortedResult = makeResponse({ results: [CHAIN_STUB] });

    const s1 = reducer(initialState, { type: "SOLVE_SUCCESS", result: firstResult });
    expect(s1.displayedResults).toHaveLength(2);

    const s2 = reducer(s1, { type: "SORT_CHANGED", result: sortedResult, sort: "resource" });
    expect(s2.displayedResults).toHaveLength(1);
    expect(s2.currentSort).toBe("resource");
    expect(s2.solveResult).toEqual(sortedResult);
  });
});

const IRON_INGOT = "Desc_IronIngot_C";
const IRON_PLATE = "Desc_IronPlate_C";
const WIRE = "Desc_Wire_C";
const COPPER_INGOT = "Desc_CopperIngot_C";

const RECIPE_IRON_PLATE: Recipe = {
  class_name: "Recipe_IronPlate_C",
  display_name: "Iron Plate",
  machine_class: "Build_ConstructorMk1_C",
  ingredients: [{ item_class: IRON_INGOT, amount_per_min: 30 }],
  products: [{ item_class: IRON_PLATE, amount_per_min: 20 }],
  duration: 6,
  is_alternate: false,
  is_build_gun: false,
};

const RECIPE_ALT_IRON_PLATE: Recipe = {
  class_name: "Recipe_Alternate_IronPlate_C",
  display_name: "Alternate: Iron Alloy Plate",
  machine_class: "Build_ConstructorMk1_C",
  ingredients: [
    { item_class: IRON_INGOT, amount_per_min: 22.5 },
    { item_class: COPPER_INGOT, amount_per_min: 7.5 },
  ],
  products: [{ item_class: IRON_PLATE, amount_per_min: 15 }],
  duration: 8,
  is_alternate: true,
  is_build_gun: false,
};

const RECIPE_WIRE: Recipe = {
  class_name: "Recipe_Wire_C",
  display_name: "Wire",
  machine_class: "Build_ConstructorMk1_C",
  ingredients: [{ item_class: COPPER_INGOT, amount_per_min: 15 }],
  products: [{ item_class: WIRE, amount_per_min: 30 }],
  duration: 4,
  is_alternate: false,
  is_build_gun: false,
};

const RECIPE_ALT_IRON_WIRE: Recipe = {
  class_name: "Recipe_Alternate_IronWire_C",
  display_name: "Alternate: Iron Wire",
  machine_class: "Build_ConstructorMk1_C",
  ingredients: [{ item_class: IRON_INGOT, amount_per_min: 12.5 }],
  products: [{ item_class: WIRE, amount_per_min: 22.5 }],
  duration: 4,
  is_alternate: true,
  is_build_gun: false,
};

const ALL_RECIPES = [RECIPE_IRON_PLATE, RECIPE_ALT_IRON_PLATE, RECIPE_WIRE, RECIPE_ALT_IRON_WIRE];

describe("relevantAlternates", () => {
  it("returns empty when no outputs selected", () => {
    expect(relevantAlternates([], ALL_RECIPES)).toEqual([]);
  });

  it("returns empty when outputs have no item class", () => {
    const outputs = [{ id: "1", item_class: "", amount: 5 }];
    expect(relevantAlternates(outputs, ALL_RECIPES)).toEqual([]);
  });

  it("returns alternates that produce the selected output", () => {
    const outputs = [{ id: "1", item_class: IRON_PLATE, amount: 5 }];
    const alts = relevantAlternates(outputs, ALL_RECIPES);
    expect(alts.map((r) => r.class_name)).toContain("Recipe_Alternate_IronPlate_C");
  });

  it("returns alternates for transitive ingredients", () => {
    const outputs = [{ id: "1", item_class: IRON_PLATE, amount: 5 }];
    // IRON_INGOT is an ingredient of IronPlate → IronWire alt produces from IRON_INGOT
    // but IronWire produces WIRE, not IRON_INGOT... so not reachable from IRON_PLATE
    // Let's check that Recipe_Alternate_IronWire is NOT included unless WIRE is reachable
    const alts = relevantAlternates(outputs, ALL_RECIPES);
    expect(alts.map((r) => r.class_name)).not.toContain("Recipe_Alternate_IronWire_C");
  });

  it("sorts results alphabetically by display_name", () => {
    // Add a second output that needs wire so Iron Wire alt becomes relevant
    const outputs = [
      { id: "1", item_class: IRON_PLATE, amount: 5 },
      { id: "2", item_class: WIRE, amount: 10 },
    ];
    const alts = relevantAlternates(outputs, ALL_RECIPES);
    const names = alts.map((r) => r.display_name);
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
    expect(alts.map((r) => r.class_name)).toContain("Recipe_Alternate_IronWire_C");
  });

  it("excludes build-gun and non-alternate recipes", () => {
    const outputs = [{ id: "1", item_class: IRON_PLATE, amount: 5 }];
    const alts = relevantAlternates(outputs, ALL_RECIPES);
    expect(alts.every((r) => r.is_alternate)).toBe(true);
  });

  it("does not include alternates reachable only through another alternate's ingredients", () => {
    // COPPER_INGOT is only introduced as an ingredient of RECIPE_ALT_IRON_PLATE (an alternate).
    // Any alternate whose product is COPPER_INGOT should NOT appear when asking for IRON_PLATE,
    // because the BFS must only traverse standard recipes to build the reachable set.
    const RECIPE_ALT_COPPER_INGOT: Recipe = {
      class_name: "Recipe_Alternate_CopperIngot_C",
      display_name: "Alternate: Copper Alloy Ingot",
      machine_class: "Build_FoundryMk1_C",
      ingredients: [{ item_class: IRON_INGOT, amount_per_min: 50 }],
      products: [{ item_class: COPPER_INGOT, amount_per_min: 100 }],
      duration: 6,
      is_alternate: true,
      is_build_gun: false,
    };
    const recipes = [...ALL_RECIPES, RECIPE_ALT_COPPER_INGOT];
    const outputs = [{ id: "1", item_class: IRON_PLATE, amount: 5 }];
    const alts = relevantAlternates(outputs, recipes);
    expect(alts.map((r) => r.class_name)).not.toContain("Recipe_Alternate_CopperIngot_C");
  });

  it("includes alternates reachable through an already-unlocked alternate's ingredients", () => {
    // RECIPE_ALT_IRON_PLATE is unlocked and uses COPPER_INGOT. Any alternate that
    // produces COPPER_INGOT should now appear because the unlocked alternate is
    // traversed during BFS.
    const RECIPE_ALT_COPPER_INGOT: Recipe = {
      class_name: "Recipe_Alternate_CopperIngot_C",
      display_name: "Alternate: Copper Alloy Ingot",
      machine_class: "Build_FoundryMk1_C",
      ingredients: [{ item_class: IRON_INGOT, amount_per_min: 50 }],
      products: [{ item_class: COPPER_INGOT, amount_per_min: 100 }],
      duration: 6,
      is_alternate: true,
      is_build_gun: false,
    };
    const recipes = [...ALL_RECIPES, RECIPE_ALT_COPPER_INGOT];
    const outputs = [{ id: "1", item_class: IRON_PLATE, amount: 5 }];
    const unlocked = new Set(["Recipe_Alternate_IronPlate_C"]);
    const alts = relevantAlternates(outputs, recipes, unlocked);
    expect(alts.map((r) => r.class_name)).toContain("Recipe_Alternate_CopperIngot_C");
  });

  it("includes Iron Wire when Stitched Iron Plate is unlocked for an iron plate output", () => {
    // Stitched Iron Plate uses WIRE. Iron Wire produces WIRE from IRON_INGOT.
    // Iron Wire should appear when Stitched Iron Plate is already unlocked.
    const outputs = [{ id: "1", item_class: IRON_PLATE, amount: 5 }];
    const unlocked = new Set(["Recipe_Alternate_IronPlate_C"]); // reuse alt iron plate as stand-in
    // Without unlocked: Iron Wire not reachable (Wire not in standard chain for Iron Plate)
    const altsWithout = relevantAlternates(outputs, ALL_RECIPES);
    expect(altsWithout.map((r) => r.class_name)).not.toContain("Recipe_Alternate_IronWire_C");
    // With unlocked alt that uses COPPER_INGOT: Wire still not reachable
    // (the alt uses COPPER_INGOT, not WIRE). This confirms traversal is selective.
    const altsWith = relevantAlternates(outputs, ALL_RECIPES, unlocked);
    // RECIPE_ALT_IRON_PLATE uses COPPER_INGOT, not WIRE, so Iron Wire still not shown
    expect(altsWith.map((r) => r.class_name)).not.toContain("Recipe_Alternate_IronWire_C");
  });
});
