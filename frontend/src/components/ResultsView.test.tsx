import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ChainResultOut, SolveResponse } from "../api/types";
import ResultsView from "./ResultsView";

const ITEM_MAP = new Map([
  ["Desc_IronIngot_C", "Iron Ingot"],
  ["Desc_Wire_C", "Wire"],
]);

const CHAIN_A: ChainResultOut = {
  machine_groups: [
    {
      recipe_class: "Recipe_IronPlate_C",
      recipe_display_name: "Iron Plate",
      machine_class: "Build_ConstructorMk1_C",
      machine_count: 2,
      clock_speed_pct: 100,
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

const CHAIN_B: ChainResultOut = {
  ...CHAIN_A,
  machine_groups: [
    {
      // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
      ...CHAIN_A.machine_groups[0]!,
      recipe_class: "Recipe_IronPlate_Alt_C",
      recipe_display_name: "Iron Plate (Alt)",
    },
  ],
  total_resource_consumed: 120,
};

const DEFICIT_CHAIN: ChainResultOut = {
  ...CHAIN_A,
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

function makeResponse(overrides: Partial<SolveResponse> = {}): SolveResponse {
  return {
    solve_id: "test-uuid",
    total_count: 1,
    page: 1,
    page_size: 10,
    cap_reached: false,
    results: [CHAIN_A],
    failure: null,
    all_chains_have_deficit: false,
    warnings: null,
    ...overrides,
  };
}

describe("ResultsView — basic rendering", () => {
  it("renders chain cards for each displayed result", () => {
    render(
      <ResultsView
        response={makeResponse({ total_count: 2, results: [CHAIN_A, CHAIN_B] })}
        displayedResults={[CHAIN_A, CHAIN_B]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getAllByTestId("chain-card")).toHaveLength(2);
  });

  it("shows result count in header", () => {
    render(
      <ResultsView
        response={makeResponse({ total_count: 5 })}
        displayedResults={[CHAIN_A]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/1 of 5/)).toBeInTheDocument();
  });
});

describe("ResultsView — bar scaling", () => {
  it("best chain gets 50% bar, worst gets 100% (relative scaling)", () => {
    render(
      <ResultsView
        response={makeResponse({ total_count: 2, results: [CHAIN_A, CHAIN_B] })}
        displayedResults={[CHAIN_A, CHAIN_B]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    // CHAIN_A consumed 60, CHAIN_B consumed 120 → max = 120
    // CHAIN_A bar = 60/120 * 100 = 50%; CHAIN_B bar = 100%
    const bars = document.querySelectorAll("[style*='width:']");
    const widths = Array.from(bars).map((el) =>
      (el as HTMLElement).style.width,
    );
    expect(widths).toContain("50%");
    expect(widths).toContain("100%");
  });
});

describe("ResultsView — deficit", () => {
  it("deficit chain shows warning symbol", () => {
    render(
      <ResultsView
        response={makeResponse({ results: [DEFICIT_CHAIN] })}
        displayedResults={[DEFICIT_CHAIN]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Budget deficit")).toBeInTheDocument();
  });

  it("shows all-deficit banner when all_chains_have_deficit is true", () => {
    render(
      <ResultsView
        response={makeResponse({
          results: [DEFICIT_CHAIN],
          all_chains_have_deficit: true,
        })}
        displayedResults={[DEFICIT_CHAIN]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("all-deficit-notice")).toBeInTheDocument();
  });
});

describe("ResultsView — pagination", () => {
  it("shows Load more button when more results exist", () => {
    render(
      <ResultsView
        response={makeResponse({ total_count: 5 })}
        displayedResults={[CHAIN_A]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("load-more-button")).toBeInTheDocument();
    expect(screen.getByText(/4 remaining/)).toBeInTheDocument();
  });

  it("does not show Load more button when all results are displayed", () => {
    render(
      <ResultsView
        response={makeResponse({ total_count: 1 })}
        displayedResults={[CHAIN_A]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("load-more-button")).not.toBeInTheDocument();
  });

  it("calls onLoadMore when Load more is clicked", () => {
    const onLoadMore = vi.fn();
    render(
      <ResultsView
        response={makeResponse({ total_count: 5 })}
        displayedResults={[CHAIN_A]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={onLoadMore}
        onSortChange={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("load-more-button"));
    expect(onLoadMore).toHaveBeenCalledOnce();
  });

  it("disables Load more button while loading", () => {
    render(
      <ResultsView
        response={makeResponse({ total_count: 5 })}
        displayedResults={[CHAIN_A]}
        isLoadingMore={true}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("load-more-button")).toBeDisabled();
  });

  it("appends new cards after Load more without replacing existing ones", () => {
    const { rerender } = render(
      <ResultsView
        response={makeResponse({ total_count: 2 })}
        displayedResults={[CHAIN_A]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getAllByTestId("chain-card")).toHaveLength(1);

    // Simulate load more completing with a new result appended
    rerender(
      <ResultsView
        response={makeResponse({ total_count: 2, page: 2 })}
        displayedResults={[CHAIN_A, CHAIN_B]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getAllByTestId("chain-card")).toHaveLength(2);
    // Both recipes visible
    expect(screen.getByText("Iron Plate")).toBeInTheDocument();
    expect(screen.getByText("Iron Plate (Alt)")).toBeInTheDocument();
  });
});

describe("ResultsView — sort", () => {
  it("renders sort selector", () => {
    render(
      <ResultsView
        response={makeResponse({ total_count: 2, results: [CHAIN_A, CHAIN_B] })}
        displayedResults={[CHAIN_A, CHAIN_B]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("combobox", { name: /sort/i })).toBeInTheDocument();
  });

  it("calls onSortChange when sort is changed", () => {
    const onSortChange = vi.fn();
    render(
      <ResultsView
        response={makeResponse({ total_count: 2, results: [CHAIN_A, CHAIN_B] })}
        displayedResults={[CHAIN_A, CHAIN_B]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={onSortChange}
      />,
    );
    fireEvent.change(screen.getByRole("combobox", { name: /sort/i }), {
      target: { value: "resource" },
    });
    expect(onSortChange).toHaveBeenCalledWith("resource");
  });
});

describe("ResultsView — cap reached notice", () => {
  it("shows cap-reached notice when cap_reached is true", () => {
    render(
      <ResultsView
        response={makeResponse({ cap_reached: true })}
        displayedResults={[CHAIN_A]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("cap-reached-notice")).toBeInTheDocument();
    expect(screen.getByText(/chain limit/i)).toBeInTheDocument();
  });

  it("does not show cap-reached notice when cap_reached is false", () => {
    render(
      <ResultsView
        response={makeResponse({ cap_reached: false })}
        displayedResults={[CHAIN_A]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("cap-reached-notice")).not.toBeInTheDocument();
  });
});

describe("ResultsView — Phase 1 failure", () => {
  it("shows Phase 1 failure card with message", () => {
    render(
      <ResultsView
        response={makeResponse({
          total_count: 0,
          results: [],
          failure: {
            failure_type: "phase1",
            message: "No recipe found for Desc_ModularFrame_C",
            item_class: "Desc_ModularFrame_C",
            chain_deficits: null,
          },
        })}
        displayedResults={[]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("phase1-failure")).toBeInTheDocument();
    expect(screen.getByText(/No recipe found for Desc_ModularFrame_C/)).toBeInTheDocument();
  });

  it("does not show chain cards for Phase 1 failure", () => {
    render(
      <ResultsView
        response={makeResponse({
          total_count: 0,
          results: [],
          failure: {
            failure_type: "phase1",
            message: "No recipe path.",
            item_class: null,
            chain_deficits: null,
          },
        })}
        displayedResults={[]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("chain-card")).not.toBeInTheDocument();
  });
});

describe("ResultsView — Phase 2 failure", () => {
  it("shows Phase 2 failure summary card", () => {
    render(
      <ResultsView
        response={makeResponse({
          total_count: 0,
          results: [],
          failure: {
            failure_type: "phase2",
            message: "All chains have deficits.",
            item_class: null,
            chain_deficits: [{ Desc_IronIngot_C: 108 }],
          },
        })}
        displayedResults={[]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("phase2-failure")).toBeInTheDocument();
    expect(screen.getByText(/No viable chains found/)).toBeInTheDocument();
  });

  it("Phase 2 failure card expands to show per-chain deficits", () => {
    render(
      <ResultsView
        response={makeResponse({
          total_count: 0,
          results: [],
          failure: {
            failure_type: "phase2",
            message: "All chains have deficits.",
            item_class: null,
            chain_deficits: [{ Desc_IronIngot_C: 108 }],
          },
        })}
        displayedResults={[]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByTestId("chain-deficits")).toBeInTheDocument();
    // Item name resolved from ITEM_MAP
    expect(screen.getByText(/Iron Ingot/)).toBeInTheDocument();
    expect(screen.getByText(/108\.00 \/min/)).toBeInTheDocument();
  });

  it("Phase 2 failure renders correct message when no chain_deficits", () => {
    render(
      <ResultsView
        response={makeResponse({
          total_count: 0,
          results: [],
          failure: {
            failure_type: "phase2",
            message: "All chains have deficits.",
            item_class: null,
            chain_deficits: null,
          },
        })}
        displayedResults={[]}
        isLoadingMore={false}
        currentSort="resource"
        itemNameMap={ITEM_MAP}
        onLoadMore={vi.fn()}
        onSortChange={vi.fn()}
      />,
    );
    expect(screen.getByTestId("phase2-failure")).toBeInTheDocument();
    // No expand button since no deficits to show
    expect(screen.queryByText(/Show per-chain breakdown/)).not.toBeInTheDocument();
  });
});
