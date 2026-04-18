import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import AlternatesPanel from "./AlternatesPanel";
import type { Recipe } from "../api/types";

const ALT_RECIPE: Recipe = {
  class_name: "Recipe_Alternate_IronWire_C",
  display_name: "Alternate: Iron Wire",
  machine_class: "Build_ConstructorMk1_C",
  ingredients: [{ item_class: "Desc_IronIngot_C", amount_per_min: 12.5 }],
  products: [{ item_class: "Desc_Wire_C", amount_per_min: 22.5 }],
  duration: 4,
  is_alternate: true,
  is_build_gun: false,
};

describe("AlternatesPanel", () => {
  it("shows placeholder when no alternates available", () => {
    render(
      <AlternatesPanel alternates={[]} unlockedAlternates={[]} dispatch={vi.fn()} />,
    );
    expect(screen.getByText(/select desired outputs/i)).toBeInTheDocument();
  });

  it("renders alternate recipe checkboxes", () => {
    render(
      <AlternatesPanel
        alternates={[ALT_RECIPE]}
        unlockedAlternates={[]}
        dispatch={vi.fn()}
      />,
    );
    expect(screen.getByText("Alternate: Iron Wire")).toBeInTheDocument();
    expect(screen.getByRole("checkbox")).not.toBeChecked();
  });

  it("shows checked state for unlocked alternates", () => {
    render(
      <AlternatesPanel
        alternates={[ALT_RECIPE]}
        unlockedAlternates={["Recipe_Alternate_IronWire_C"]}
        dispatch={vi.fn()}
      />,
    );
    expect(screen.getByRole("checkbox")).toBeChecked();
  });

  it("dispatches TOGGLE_ALTERNATE when checkbox clicked", () => {
    const dispatch = vi.fn();
    render(
      <AlternatesPanel
        alternates={[ALT_RECIPE]}
        unlockedAlternates={[]}
        dispatch={dispatch}
      />,
    );
    fireEvent.click(screen.getByRole("checkbox"));
    expect(dispatch).toHaveBeenCalledWith({
      type: "TOGGLE_ALTERNATE",
      class_name: "Recipe_Alternate_IronWire_C",
    });
  });
});
