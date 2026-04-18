export interface Item {
  class_name: string;
  display_name: string;
}

export interface ItemAmount {
  item_class: string;
  amount_per_min: number;
}

export interface Recipe {
  class_name: string;
  display_name: string;
  machine_class: string;
  ingredients: ItemAmount[];
  products: ItemAmount[];
  duration: number;
  is_alternate: boolean;
  is_build_gun: boolean;
}

export interface MachineGroupOut {
  recipe_class: string;
  recipe_display_name: string;
  machine_class: string;
  machine_count: number;
  clock_speed_pct: number;
  exact_recipe_rate: number;
}

export interface BudgetEntryOut {
  item_class: string;
  available: number;
  consumed: number;
  delta: number;
}

export interface ChainResultOut {
  machine_groups: MachineGroupOut[];
  raw_resource_consumption: Record<string, number>;
  implicit_outputs: Record<string, number>;
  has_cycle: boolean;
  budget: Record<string, BudgetEntryOut>;
  has_deficit: boolean;
  total_resource_consumed: number;
}

export interface SolveFailureOut {
  failure_type: "phase1" | "phase2";
  message: string;
  item_class: string | null;
  chain_deficits: Record<string, number>[] | null;
}

export interface SolveResponse {
  solve_id: string | null;
  total_count: number;
  page: number;
  page_size: number;
  cap_reached: boolean;
  results: ChainResultOut[];
  failure: SolveFailureOut | null;
  all_chains_have_deficit: boolean;
  warnings: string[] | null;
}

export interface SolveRequest {
  inputs?: Record<string, number>;
  outputs: Record<string, number>;
  unlocked_alternates?: string[];
  clocking_available?: boolean;
  page_size?: number;
}

export interface ResultsParams {
  sort?: "resource";
  page?: number;
  page_size?: number;
}
