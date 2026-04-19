import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ChainResultOut } from "../api/types";
import ChainCard from "./ChainCard";

const ITEM_MAP = new Map([
  ["Desc_IronIngot_C", "Iron Ingot"],
  ["Desc_IronPlate_C", "Iron Plate"],
  ["Desc_IronRod_C", "Iron Rod"],
]);

const BASE_CHAIN: ChainResultOut = {
  machine_groups: [
    {
      recipe_class: "Recipe_IronPlate_C",
      recipe_display_name: "Iron Plate",
      machine_class: "Build_ConstructorMk1_C",
      machine_count: 2,
      clock_speed_pct: 83.33,
      exact_recipe_rate: 2,
    },
  ],
  raw_resource_consumption: { Desc_IronIngot_C: 60 },
  implicit_outputs: {},
  has_cycle: false,
  budget: {
    Desc_IronIngot_C: {
      item_class: "Desc_IronIngot_C",
      available: 120,
      consumed: 60,
      delta: 60,
    },
  },
  has_deficit: false,
  total_resource_consumed: 60,
};

const DEFICIT_CHAIN: ChainResultOut = {
  ...BASE_CHAIN,
  has_deficit: true,
  budget: {
    Desc_IronIngot_C: {
      item_class: "Desc_IronIngot_C",
      available: 30,
      consumed: 60,
      delta: -30,
    },
  },
};

const IMPLICIT_CHAIN: ChainResultOut = {
  ...BASE_CHAIN,
  implicit_outputs: { Desc_IronRod_C: 15.5 },
};

describe("ChainCard", () => {
  it("renders machine group recipe name and count", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={75} itemNameMap={ITEM_MAP} />);
    expect(screen.getByText("Iron Plate")).toBeInTheDocument();
    expect(screen.getByText(/2×/)).toBeInTheDocument();
  });

  it("formats machine class name", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={75} itemNameMap={ITEM_MAP} />);
    expect(screen.getByText(/Constructor Mk 1/)).toBeInTheDocument();
  });

  it("rounds clock speed up", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={75} itemNameMap={ITEM_MAP} />);
    // ceil(83.33) = 84
    expect(screen.getByText(/84%/)).toBeInTheDocument();
  });

  it("renders resource bar with correct percentage width", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={60} itemNameMap={ITEM_MAP} />);
    const bar = document.querySelector('[style*="width: 60%"]');
    expect(bar).toBeInTheDocument();
  });

  it("shows resource consumption total", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={100} itemNameMap={ITEM_MAP} />);
    expect(screen.getByText(/60 \/min/)).toBeInTheDocument();
  });

  it("does not show deficit warning for non-deficit chain", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={75} itemNameMap={ITEM_MAP} />);
    expect(screen.queryByLabelText("Budget deficit")).not.toBeInTheDocument();
  });

  it("shows deficit warning symbol for deficit chain", () => {
    render(<ChainCard chain={DEFICIT_CHAIN} barPct={100} itemNameMap={ITEM_MAP} />);
    expect(screen.getByLabelText("Budget deficit")).toBeInTheDocument();
  });

  it("detail table is hidden initially", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={75} itemNameMap={ITEM_MAP} />);
    expect(screen.queryByTestId("detail-table")).not.toBeInTheDocument();
  });

  it("expands detail table on click", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={75} itemNameMap={ITEM_MAP} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByTestId("detail-table")).toBeInTheDocument();
  });

  it("detail table shows resource name from itemNameMap", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={75} itemNameMap={ITEM_MAP} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("Iron Ingot")).toBeInTheDocument();
  });

  it("detail table shows budget, consumed, and delta", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={75} itemNameMap={ITEM_MAP} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("120")).toBeInTheDocument(); // available
    expect(screen.getByText("60")).toBeInTheDocument(); // consumed
    expect(screen.getByText("+60")).toBeInTheDocument(); // delta
  });

  it("deficit detail table shows negative delta", () => {
    render(<ChainCard chain={DEFICIT_CHAIN} barPct={100} itemNameMap={ITEM_MAP} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("-30")).toBeInTheDocument();
  });

  it("collapses detail table on second click", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={75} itemNameMap={ITEM_MAP} />);
    const button = screen.getByRole("button");
    fireEvent.click(button);
    expect(screen.getByTestId("detail-table")).toBeInTheDocument();
    fireEvent.click(button);
    expect(screen.queryByTestId("detail-table")).not.toBeInTheDocument();
  });

  it("shows implicit outputs when present", () => {
    render(<ChainCard chain={IMPLICIT_CHAIN} barPct={75} itemNameMap={ITEM_MAP} />);
    expect(screen.getByText(/Iron Rod/)).toBeInTheDocument();
    expect(screen.getByText(/15\.5 \/min/)).toBeInTheDocument();
  });

  it("does not show implicit outputs section when empty", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={75} itemNameMap={ITEM_MAP} />);
    expect(screen.queryByText(/Side outputs/i)).not.toBeInTheDocument();
  });

  it("falls back to item class when name not in map", () => {
    render(<ChainCard chain={DEFICIT_CHAIN} barPct={100} itemNameMap={new Map()} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("Desc_IronIngot_C")).toBeInTheDocument();
  });

  it("shows dashes for zero available budget", () => {
    const chain: ChainResultOut = {
      ...BASE_CHAIN,
      budget: {
        Desc_IronIngot_C: {
          item_class: "Desc_IronIngot_C",
          available: 0,
          consumed: 60,
          delta: -60,
        },
      },
    };
    render(<ChainCard chain={chain} barPct={100} itemNameMap={ITEM_MAP} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("bar uses amber colour class for deficit chains", () => {
    render(<ChainCard chain={DEFICIT_CHAIN} barPct={100} itemNameMap={ITEM_MAP} />);
    const bar = document.querySelector(".bg-amber-500");
    expect(bar).toBeInTheDocument();
  });

  it("bar uses blue colour class for non-deficit chains", () => {
    render(<ChainCard chain={BASE_CHAIN} barPct={75} itemNameMap={ITEM_MAP} />);
    const bar = document.querySelector(".bg-blue-500");
    expect(bar).toBeInTheDocument();
  });
});
