import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getItems, getRecipes, getSolveResults, postSolve } from "./client";
import type { ChainResultOut, Item, Recipe, SolveResponse } from "./types";

const ITEM: Item = { class_name: "Desc_IronPlate_C", display_name: "Iron Plate", is_raw_resource: false };
const RECIPE: Recipe = {
  class_name: "Recipe_IronPlate_C",
  display_name: "Iron Plate",
  machine_class: "Build_ConstructorMk1_C",
  ingredients: [{ item_class: "Desc_IronIngot_C", amount_per_min: 30 }],
  products: [{ item_class: "Desc_IronPlate_C", amount_per_min: 20 }],
  duration: 6,
  is_alternate: false,
  is_build_gun: false,
};
const CHAIN: ChainResultOut = {
  machine_groups: [
    {
      recipe_class: "Recipe_IronPlate_C",
      recipe_display_name: "Iron Plate",
      machine_class: "Build_ConstructorMk1_C",
      machine_count: 1,
      clock_speed_pct: 100,
      exact_recipe_rate: 1,
    },
  ],
  raw_resource_consumption: { Desc_IronIngot_C: 30 },
  implicit_outputs: {},
  has_cycle: false,
  budget: {
    Desc_IronIngot_C: {
      item_class: "Desc_IronIngot_C",
      available: 30,
      consumed: 30,
      delta: 0,
    },
  },
  has_deficit: false,
  total_resource_consumed: 30,
};
const SOLVE_RESPONSE: SolveResponse = {
  solve_id: "test-uuid",
  total_count: 1,
  page: 1,
  page_size: 10,
  cap_reached: false,
  results: [CHAIN],
  failure: null,
  all_chains_have_deficit: false,
  warnings: null,
};

function mockFetch(body: unknown, status = 200): void {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

beforeEach(() => {
  vi.spyOn(globalThis, "fetch");
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("getItems", () => {
  it("fetches /api/items and returns items", async () => {
    mockFetch([ITEM]);
    const result = await getItems();
    expect(result).toEqual([ITEM]);
    expect(fetch).toHaveBeenCalledWith("/api/items", undefined);
  });
});

describe("getRecipes", () => {
  it("fetches /api/recipes and returns recipes", async () => {
    mockFetch([RECIPE]);
    const result = await getRecipes();
    expect(result).toEqual([RECIPE]);
    expect(fetch).toHaveBeenCalledWith("/api/recipes", undefined);
  });
});

describe("postSolve", () => {
  it("POSTs /api/solve with JSON body and returns response", async () => {
    mockFetch(SOLVE_RESPONSE);
    const request = { outputs: { Desc_IronPlate_C: 20 } };
    const result = await postSolve(request);
    expect(result).toEqual(SOLVE_RESPONSE);
    expect(fetch).toHaveBeenCalledWith(
      "/api/solve",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      }),
    );
  });
});

describe("getSolveResults", () => {
  it("fetches /api/solve/{id}/results without params", async () => {
    mockFetch(SOLVE_RESPONSE);
    const result = await getSolveResults("test-uuid");
    expect(result).toEqual(SOLVE_RESPONSE);
    expect(fetch).toHaveBeenCalledWith("/api/solve/test-uuid/results", undefined);
  });

  it("appends query params when provided", async () => {
    mockFetch(SOLVE_RESPONSE);
    await getSolveResults("test-uuid", { sort: "resource", page: 2, page_size: 5 });
    expect(fetch).toHaveBeenCalledWith(
      "/api/solve/test-uuid/results?sort=resource&page=2&page_size=5",
      undefined,
    );
  });

  it("omits query string when no params given", async () => {
    mockFetch(SOLVE_RESPONSE);
    await getSolveResults("test-uuid", {});
    expect(fetch).toHaveBeenCalledWith("/api/solve/test-uuid/results", undefined);
  });
});

describe("error handling", () => {
  it("throws on non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response("Not found", { status: 404 }),
    );
    await expect(getItems()).rejects.toThrow("API 404");
  });
});
