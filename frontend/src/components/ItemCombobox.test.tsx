import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ItemCombobox from "./ItemCombobox";
import type { Item } from "../api/types";

const ITEMS: Item[] = [
  { class_name: "Desc_IronIngot_C", display_name: "Iron Ingot" },
  { class_name: "Desc_CopperIngot_C", display_name: "Copper Ingot" },
  { class_name: "Desc_IronPlate_C", display_name: "Iron Plate" },
];

describe("ItemCombobox", () => {
  it("renders with placeholder when no item selected", () => {
    render(<ItemCombobox value="" items={ITEMS} onChange={vi.fn()} />);
    expect(screen.getByPlaceholderText("Select item…")).toBeInTheDocument();
  });

  it("shows selected item display name when value is set", () => {
    render(<ItemCombobox value="Desc_IronIngot_C" items={ITEMS} onChange={vi.fn()} />);
    expect(screen.getByDisplayValue("Iron Ingot")).toBeInTheDocument();
  });

  it("shows 'Start typing to search' hint when focused with empty query", () => {
    render(<ItemCombobox value="" items={ITEMS} onChange={vi.fn()} />);
    fireEvent.focus(screen.getByRole("textbox"));
    expect(screen.getByText(/start typing to search/i)).toBeInTheDocument();
  });

  it("filters items by typed query", () => {
    render(<ItemCombobox value="" items={ITEMS} onChange={vi.fn()} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "iron" } });
    expect(screen.getByText("Iron Ingot")).toBeInTheDocument();
    expect(screen.getByText("Iron Plate")).toBeInTheDocument();
    expect(screen.queryByText("Copper Ingot")).not.toBeInTheDocument();
  });

  it("shows 'No matches' for unrecognised query", () => {
    render(<ItemCombobox value="" items={ITEMS} onChange={vi.fn()} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "zzz" } });
    expect(screen.getByText(/no matches/i)).toBeInTheDocument();
  });

  it("calls onChange with class_name when item clicked", () => {
    const onChange = vi.fn();
    render(<ItemCombobox value="" items={ITEMS} onChange={onChange} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "copper" } });
    fireEvent.click(screen.getByText("Copper Ingot"));
    expect(onChange).toHaveBeenCalledWith("Desc_CopperIngot_C");
  });

  it("highlights the currently selected item in the dropdown", () => {
    render(<ItemCombobox value="Desc_IronIngot_C" items={ITEMS} onChange={vi.fn()} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "iron" } });
    const highlighted = screen.getByText("Iron Ingot").closest("li");
    expect(highlighted?.className).toMatch(/text-blue-300/);
  });
});
