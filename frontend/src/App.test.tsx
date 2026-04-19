import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "./App";
import type { Item } from "./api/types";

const ITEMS: Item[] = [
  { class_name: "Desc_IronIngot_C", display_name: "Iron Ingot", is_raw_resource: false },
  { class_name: "Desc_CopperIngot_C", display_name: "Copper Ingot", is_raw_resource: false },
];

function mockFetchSequence(responses: [unknown, number?][]): void {
  const spy = vi.spyOn(globalThis, "fetch");
  for (const [body, status = 200] of responses) {
    spy.mockResolvedValueOnce(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    );
  }
}

function mockFetch(body: unknown, status = 200): void {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

beforeEach(() => {
  mockFetch([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  it("renders the app title", () => {
    render(<App />);
    expect(screen.getByText("ficsolver")).toBeInTheDocument();
  });

  it("renders all panel sections", () => {
    render(<App />);
    expect(screen.getByLabelText("Settings")).toBeInTheDocument();
    expect(screen.getByLabelText("Available Inputs")).toBeInTheDocument();
    expect(screen.getByLabelText("Desired Outputs")).toBeInTheDocument();
    expect(screen.getByLabelText("Alternate Recipes")).toBeInTheDocument();
  });

  it("renders the Solve button", () => {
    render(<App />);
    expect(screen.getByRole("button", { name: /solve/i })).toBeInTheDocument();
  });

  it("Solve button is disabled when no outputs configured", () => {
    render(<App />);
    expect(screen.getByRole("button", { name: /solve/i })).toBeDisabled();
  });

  it("shows data loading indicator initially", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
    render(<App />);
    expect(screen.getByText(/loading game data/i)).toBeInTheDocument();
  });

  it("shows data error when fetch fails", async () => {
    vi.restoreAllMocks();
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText(/failed to load game data/i)).toBeInTheDocument();
    });
  });

  it("hides loading indicator after items load", async () => {
    mockFetchSequence([[ITEMS], [[]]]);
    render(<App />);
    await waitFor(() => {
      expect(screen.queryByText(/loading game data/i)).not.toBeInTheDocument();
    });
  });

  it("populates input combobox with items from API", async () => {
    mockFetchSequence([[ITEMS], [[]]]);
    render(<App />);
    await waitFor(() => expect(screen.getByText(/\+ add input/i)).not.toBeDisabled());
    fireEvent.click(screen.getByText(/\+ add input/i));
    fireEvent.change(screen.getByLabelText("Input item"), { target: { value: "ingot" } });
    expect(screen.getByText("Iron Ingot")).toBeInTheDocument();
    expect(screen.getByText("Copper Ingot")).toBeInTheDocument();
  });

  it("populates output combobox with items from API", async () => {
    mockFetchSequence([[ITEMS], [[]]]);
    render(<App />);
    await waitFor(() => expect(screen.getByText(/\+ add output/i)).not.toBeDisabled());
    fireEvent.click(screen.getByText(/\+ add output/i));
    fireEvent.change(screen.getByLabelText("Output item"), { target: { value: "ingot" } });
    expect(screen.getByText("Iron Ingot")).toBeInTheDocument();
    expect(screen.getByText("Copper Ingot")).toBeInTheDocument();
  });

  it("shows no matches when API returns no items", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText(/\+ add input/i)).not.toBeDisabled());
    fireEvent.click(screen.getByText(/\+ add input/i));
    fireEvent.change(screen.getByLabelText("Input item"), { target: { value: "iron" } });
    expect(screen.queryByText("Iron Ingot")).not.toBeInTheDocument();
    expect(screen.getByText(/no matches/i)).toBeInTheDocument();
  });
});
