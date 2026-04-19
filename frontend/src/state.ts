import type { ChainResultOut, Item, Recipe, SolveResponse } from "./api/types";

export type SortKey = "resource";

export interface ItemEntry {
  id: string;
  item_class: string;
  amount: number;
}

export type SolverStatus = "idle" | "loading" | "success" | "error";

export interface AppState {
  inputs: ItemEntry[];
  outputs: ItemEntry[];
  unlockedAlternates: string[];
  clockingAvailable: boolean;
  solverStatus: SolverStatus;
  solveResult: SolveResponse | null;
  solveError: string | null;
  items: Item[];
  recipes: Recipe[];
  dataLoading: boolean;
  dataError: string | null;
  displayedResults: ChainResultOut[];
  currentSort: SortKey;
  isLoadingMore: boolean;
}

export type Action =
  | { type: "ADD_INPUT" }
  | { type: "REMOVE_INPUT"; id: string }
  | { type: "UPDATE_INPUT_CLASS"; id: string; item_class: string }
  | { type: "UPDATE_INPUT_AMOUNT"; id: string; amount: number }
  | { type: "ADD_OUTPUT" }
  | { type: "REMOVE_OUTPUT"; id: string }
  | { type: "UPDATE_OUTPUT_CLASS"; id: string; item_class: string }
  | { type: "UPDATE_OUTPUT_AMOUNT"; id: string; amount: number }
  | { type: "TOGGLE_ALTERNATE"; class_name: string }
  | { type: "SET_CLOCKING"; value: boolean }
  | { type: "SET_ITEMS"; items: Item[] }
  | { type: "SET_RECIPES"; recipes: Recipe[] }
  | { type: "DATA_ERROR"; error: string }
  | { type: "SOLVE_START" }
  | { type: "SOLVE_SUCCESS"; result: SolveResponse }
  | { type: "SOLVE_ERROR"; error: string }
  | { type: "LOAD_MORE_START" }
  | { type: "LOAD_MORE_SUCCESS"; result: SolveResponse }
  | { type: "SORT_CHANGED"; result: SolveResponse; sort: SortKey };

let _nextId = 1;

export function resetIdCounter(): void {
  _nextId = 1;
}

function newId(): string {
  return String(_nextId++);
}

export const initialState: AppState = {
  inputs: [],
  outputs: [],
  unlockedAlternates: [],
  clockingAvailable: true,
  solverStatus: "idle",
  solveResult: null,
  solveError: null,
  items: [],
  recipes: [],
  dataLoading: true,
  dataError: null,
  displayedResults: [],
  currentSort: "resource",
  isLoadingMore: false,
};

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "ADD_INPUT":
      return {
        ...state,
        inputs: [...state.inputs, { id: newId(), item_class: "", amount: 0 }],
      };
    case "REMOVE_INPUT":
      return { ...state, inputs: state.inputs.filter((e) => e.id !== action.id) };
    case "UPDATE_INPUT_CLASS":
      return {
        ...state,
        inputs: state.inputs.map((e) =>
          e.id === action.id ? { ...e, item_class: action.item_class } : e,
        ),
      };
    case "UPDATE_INPUT_AMOUNT":
      return {
        ...state,
        inputs: state.inputs.map((e) =>
          e.id === action.id ? { ...e, amount: action.amount } : e,
        ),
      };
    case "ADD_OUTPUT":
      if (state.outputs.length >= 10) return state;
      return {
        ...state,
        outputs: [...state.outputs, { id: newId(), item_class: "", amount: 0 }],
      };
    case "REMOVE_OUTPUT":
      return { ...state, outputs: state.outputs.filter((e) => e.id !== action.id) };
    case "UPDATE_OUTPUT_CLASS":
      return {
        ...state,
        outputs: state.outputs.map((e) =>
          e.id === action.id ? { ...e, item_class: action.item_class } : e,
        ),
      };
    case "UPDATE_OUTPUT_AMOUNT":
      return {
        ...state,
        outputs: state.outputs.map((e) =>
          e.id === action.id ? { ...e, amount: action.amount } : e,
        ),
      };
    case "TOGGLE_ALTERNATE": {
      const has = state.unlockedAlternates.includes(action.class_name);
      return {
        ...state,
        unlockedAlternates: has
          ? state.unlockedAlternates.filter((c) => c !== action.class_name)
          : [...state.unlockedAlternates, action.class_name],
      };
    }
    case "SET_CLOCKING":
      return { ...state, clockingAvailable: action.value };
    case "SET_ITEMS":
      return { ...state, items: action.items, dataLoading: false };
    case "SET_RECIPES":
      return { ...state, recipes: action.recipes };
    case "DATA_ERROR":
      return { ...state, dataLoading: false, dataError: action.error };
    case "SOLVE_START":
      return {
        ...state,
        solverStatus: "loading",
        solveResult: null,
        solveError: null,
        displayedResults: [],
        isLoadingMore: false,
      };
    case "SOLVE_SUCCESS":
      return {
        ...state,
        solverStatus: "success",
        solveResult: action.result,
        displayedResults: action.result.results,
        isLoadingMore: false,
      };
    case "SOLVE_ERROR":
      return { ...state, solverStatus: "error", solveError: action.error };
    case "LOAD_MORE_START":
      return { ...state, isLoadingMore: true };
    case "LOAD_MORE_SUCCESS":
      return {
        ...state,
        isLoadingMore: false,
        solveResult: action.result,
        displayedResults: [...state.displayedResults, ...action.result.results],
      };
    case "SORT_CHANGED":
      return {
        ...state,
        currentSort: action.sort,
        solveResult: action.result,
        displayedResults: action.result.results,
      };
    default:
      return state;
  }
}

export function relevantAlternates(
  outputs: ItemEntry[],
  recipes: Recipe[],
  unlockedAlternates: ReadonlySet<string> = new Set(),
): Recipe[] {
  const outputClasses = outputs.map((o) => o.item_class).filter(Boolean);
  if (outputClasses.length === 0) return [];

  const reachable = new Set<string>(outputClasses);
  const queue = [...outputClasses];

  while (queue.length > 0) {
    const item = queue.shift();
    if (item === undefined) break;
    for (const recipe of recipes) {
      // Traverse standard recipes and already-unlocked alternates to find what
      // ingredients are reachable from the desired outputs.
      const shouldTraverse =
        !recipe.is_alternate || unlockedAlternates.has(recipe.class_name);
      if (shouldTraverse && recipe.products.some((p) => p.item_class === item)) {
        for (const ing of recipe.ingredients) {
          if (!reachable.has(ing.item_class)) {
            reachable.add(ing.item_class);
            queue.push(ing.item_class);
          }
        }
      }
    }
  }

  return recipes
    .filter((r) => r.is_alternate && r.products.some((p) => reachable.has(p.item_class)))
    .sort((a, b) => a.display_name.localeCompare(b.display_name));
}
