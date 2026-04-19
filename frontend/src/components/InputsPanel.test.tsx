import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import InputsPanel from "./InputsPanel";
import type { Item } from "../api/types";
import type { ItemEntry } from "../state";

const ITEMS: Item[] = [
  { class_name: "Desc_IronIngot_C", display_name: "Iron Ingot", is_raw_resource: false, is_fluid: false },
  { class_name: "Desc_CopperIngot_C", display_name: "Copper Ingot", is_raw_resource: false, is_fluid: false },
];

const ENTRY: ItemEntry = { id: "1", item_class: "Desc_IronIngot_C", amount: 120 };

describe("InputsPanel", () => {
  it("renders the section heading", () => {
    render(<InputsPanel inputs={[]} items={ITEMS} dispatch={vi.fn()} />);
    expect(screen.getByText(/available inputs/i)).toBeInTheDocument();
  });

  it("renders an entry row for each input", () => {
    render(<InputsPanel inputs={[ENTRY]} items={ITEMS} dispatch={vi.fn()} />);
    expect(screen.getByLabelText("Input item")).toBeInTheDocument();
    expect(screen.getByLabelText("Input rate per minute")).toBeInTheDocument();
  });

  it("shows matching items in combobox dropdown when typing", () => {
    render(<InputsPanel inputs={[ENTRY]} items={ITEMS} dispatch={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Input item"), { target: { value: "ingot" } });
    expect(screen.getByText("Iron Ingot")).toBeInTheDocument();
    expect(screen.getByText("Copper Ingot")).toBeInTheDocument();
  });

  it("dispatches ADD_INPUT when Add input clicked", () => {
    const dispatch = vi.fn();
    render(<InputsPanel inputs={[]} items={ITEMS} dispatch={dispatch} />);
    fireEvent.click(screen.getByText(/\+ add input/i));
    expect(dispatch).toHaveBeenCalledWith({ type: "ADD_INPUT" });
  });

  it("dispatches REMOVE_INPUT when × clicked", () => {
    const dispatch = vi.fn();
    render(<InputsPanel inputs={[ENTRY]} items={ITEMS} dispatch={dispatch} />);
    fireEvent.click(screen.getByLabelText("Remove input"));
    expect(dispatch).toHaveBeenCalledWith({ type: "REMOVE_INPUT", id: "1" });
  });

  it("dispatches UPDATE_INPUT_CLASS when item selected from dropdown", () => {
    const dispatch = vi.fn();
    render(<InputsPanel inputs={[ENTRY]} items={ITEMS} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("Input item"), { target: { value: "Copper" } });
    fireEvent.click(screen.getByText("Copper Ingot"));
    expect(dispatch).toHaveBeenCalledWith({
      type: "UPDATE_INPUT_CLASS",
      id: "1",
      item_class: "Desc_CopperIngot_C",
    });
  });

  it("dispatches UPDATE_INPUT_AMOUNT when amount changed", () => {
    const dispatch = vi.fn();
    render(<InputsPanel inputs={[ENTRY]} items={ITEMS} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("Input rate per minute"), {
      target: { value: "240" },
    });
    expect(dispatch).toHaveBeenCalledWith({
      type: "UPDATE_INPUT_AMOUNT",
      id: "1",
      amount: 240,
    });
  });

  it("defaults amount to 0 when invalid value entered", () => {
    const dispatch = vi.fn();
    render(<InputsPanel inputs={[ENTRY]} items={ITEMS} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("Input rate per minute"), {
      target: { value: "abc" },
    });
    expect(dispatch).toHaveBeenCalledWith({
      type: "UPDATE_INPUT_AMOUNT",
      id: "1",
      amount: 0,
    });
  });
});
