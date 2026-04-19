import type { Dispatch } from "react";
import type { Item } from "../api/types";
import type { Action, ItemEntry } from "../state";

interface Props {
  inputs: ItemEntry[];
  items: Item[];
  loading?: boolean;
  dispatch: Dispatch<Action>;
}

export default function InputsPanel({ inputs, items, loading = false, dispatch }: Props) {
  return (
    <section aria-label="Available Inputs">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Available Inputs
      </h2>
      <div className="space-y-2">
        {inputs.map((entry) => (
          <div key={entry.id} className="flex gap-2 items-center">
            <select
              aria-label="Input item"
              value={entry.item_class}
              onChange={(e) =>
                dispatch({
                  type: "UPDATE_INPUT_CLASS",
                  id: entry.id,
                  item_class: e.target.value,
                })
              }
              className="flex-1 bg-gray-800 text-gray-100 rounded px-2 py-1 text-sm min-w-0"
            >
              <option value="">Select item…</option>
              {items.map((item) => (
                <option key={item.class_name} value={item.class_name}>
                  {item.display_name}
                </option>
              ))}
            </select>
            <input
              type="number"
              aria-label="Input rate per minute"
              min={0}
              step="any"
              value={entry.amount}
              onChange={(e) =>
                dispatch({
                  type: "UPDATE_INPUT_AMOUNT",
                  id: entry.id,
                  amount: parseFloat(e.target.value) || 0,
                })
              }
              className="w-24 bg-gray-800 text-gray-100 rounded px-2 py-1 text-sm"
              placeholder="/min"
            />
            <button
              type="button"
              aria-label="Remove input"
              onClick={() => dispatch({ type: "REMOVE_INPUT", id: entry.id })}
              className="text-gray-400 hover:text-red-400 text-xl leading-none flex-shrink-0"
            >
              ×
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={() => dispatch({ type: "ADD_INPUT" })}
        disabled={loading}
        className="mt-2 text-sm text-blue-400 hover:text-blue-300 disabled:text-gray-600 disabled:cursor-not-allowed"
      >
        {loading ? "+ Add input (loading…)" : "+ Add input"}
      </button>
    </section>
  );
}
