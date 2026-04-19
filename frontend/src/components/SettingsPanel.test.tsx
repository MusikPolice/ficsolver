import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import SettingsPanel from "./SettingsPanel";

describe("SettingsPanel", () => {
  it("renders the clocking checkbox checked when clockingAvailable is true", () => {
    render(
      <SettingsPanel clockingAvailable={true} excludeConverterRecipes={false} dispatch={vi.fn()} />,
    );
    const checkbox = screen.getByRole("checkbox", { name: /clocking available/i });
    expect((checkbox as HTMLInputElement).checked).toBe(true);
  });

  it("dispatches SET_CLOCKING when clocking checkbox changes", () => {
    const dispatch = vi.fn();
    render(
      <SettingsPanel clockingAvailable={true} excludeConverterRecipes={false} dispatch={dispatch} />,
    );
    fireEvent.click(screen.getByRole("checkbox", { name: /clocking available/i }));
    expect(dispatch).toHaveBeenCalledWith({ type: "SET_CLOCKING", value: false });
  });

  it("renders the converter checkbox unchecked by default", () => {
    render(
      <SettingsPanel clockingAvailable={true} excludeConverterRecipes={false} dispatch={vi.fn()} />,
    );
    const checkbox = screen.getByRole("checkbox", { name: /exclude converter recipes/i });
    expect((checkbox as HTMLInputElement).checked).toBe(false);
  });

  it("renders the converter checkbox checked when excludeConverterRecipes is true", () => {
    render(
      <SettingsPanel clockingAvailable={true} excludeConverterRecipes={true} dispatch={vi.fn()} />,
    );
    const checkbox = screen.getByRole("checkbox", { name: /exclude converter recipes/i });
    expect((checkbox as HTMLInputElement).checked).toBe(true);
  });

  it("dispatches SET_EXCLUDE_CONVERTER when converter checkbox changes", () => {
    const dispatch = vi.fn();
    render(
      <SettingsPanel clockingAvailable={true} excludeConverterRecipes={false} dispatch={dispatch} />,
    );
    fireEvent.click(screen.getByRole("checkbox", { name: /exclude converter recipes/i }));
    expect(dispatch).toHaveBeenCalledWith({ type: "SET_EXCLUDE_CONVERTER", value: true });
  });
});
