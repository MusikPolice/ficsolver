import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "./App";

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
});
