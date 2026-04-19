import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import OutputsPanel from "./OutputsPanel";
import type { Item } from "../api/types";
import type { ItemEntry } from "../state";

const ITEMS: Item[] = [
  { class_name: "Desc_ModularFrame_C", display_name: "Modular Frame", is_raw_resource: false, is_fluid: false },
  { class_name: "Desc_IronPlate_C", display_name: "Iron Plate", is_raw_resource: false, is_fluid: false },
];

const ENTRY: ItemEntry = { id: "1", item_class: "Desc_ModularFrame_C", amount: 5 };

function makeEntries(n: number): ItemEntry[] {
  return Array.from({ length: n }, (_, i) => ({
    id: String(i + 1),
    item_class: "Desc_IronPlate_C",
    amount: 1,
  }));
}

describe("OutputsPanel", () => {
  it("renders the section heading", () => {
    render(<OutputsPanel outputs={[]} items={ITEMS} dispatch={vi.fn()} />);
    expect(screen.getByText(/desired outputs/i)).toBeInTheDocument();
  });

  it("renders an entry row for each output", () => {
    render(<OutputsPanel outputs={[ENTRY]} items={ITEMS} dispatch={vi.fn()} />);
    expect(screen.getByLabelText("Output item")).toBeInTheDocument();
    expect(screen.getByLabelText("Output rate per minute")).toBeInTheDocument();
  });

  it("dispatches ADD_OUTPUT when Add output clicked", () => {
    const dispatch = vi.fn();
    render(<OutputsPanel outputs={[]} items={ITEMS} dispatch={dispatch} />);
    fireEvent.click(screen.getByText(/\+ add output/i));
    expect(dispatch).toHaveBeenCalledWith({ type: "ADD_OUTPUT" });
  });

  it("disables Add output button at 10 entries", () => {
    render(<OutputsPanel outputs={makeEntries(10)} items={ITEMS} dispatch={vi.fn()} />);
    expect(screen.getByText(/\+ add output/i)).toBeDisabled();
  });

  it("shows limit message at 10 entries", () => {
    render(<OutputsPanel outputs={makeEntries(10)} items={ITEMS} dispatch={vi.fn()} />);
    expect(screen.getByText(/maximum of 10 outputs/i)).toBeInTheDocument();
  });

  it("dispatches REMOVE_OUTPUT when × clicked", () => {
    const dispatch = vi.fn();
    render(<OutputsPanel outputs={[ENTRY]} items={ITEMS} dispatch={dispatch} />);
    fireEvent.click(screen.getByLabelText("Remove output"));
    expect(dispatch).toHaveBeenCalledWith({ type: "REMOVE_OUTPUT", id: "1" });
  });

  it("dispatches UPDATE_OUTPUT_CLASS when item selected from dropdown", () => {
    const dispatch = vi.fn();
    render(<OutputsPanel outputs={[ENTRY]} items={ITEMS} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("Output item"), { target: { value: "Iron" } });
    fireEvent.click(screen.getByText("Iron Plate"));
    expect(dispatch).toHaveBeenCalledWith({
      type: "UPDATE_OUTPUT_CLASS",
      id: "1",
      item_class: "Desc_IronPlate_C",
    });
  });

  it("dispatches UPDATE_OUTPUT_AMOUNT when amount changed", () => {
    const dispatch = vi.fn();
    render(<OutputsPanel outputs={[ENTRY]} items={ITEMS} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("Output rate per minute"), {
      target: { value: "10" },
    });
    expect(dispatch).toHaveBeenCalledWith({
      type: "UPDATE_OUTPUT_AMOUNT",
      id: "1",
      amount: 10,
    });
  });
});
