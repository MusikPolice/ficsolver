import type { Dispatch } from "react";
import type { Item } from "../api/types";
import type { Action, ItemEntry } from "../state";

const MAX_OUTPUTS = 10;

interface Props {
  outputs: ItemEntry[];
  items: Item[];
  dispatch: Dispatch<Action>;
}

export default function OutputsPanel({ outputs, items, dispatch }: Props) {
  const atLimit = outputs.length >= MAX_OUTPUTS;

  return (
    <section aria-label="Desired Outputs">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Desired Outputs
      </h2>
      <div className="space-y-2">
        {outputs.map((entry) => (
          <div key={entry.id} className="flex gap-2 items-center">
            <select
              aria-label="Output item"
              value={entry.item_class}
              onChange={(e) =>
                dispatch({
                  type: "UPDATE_OUTPUT_CLASS",
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
              aria-label="Output rate per minute"
              min={0}
              step="any"
              value={entry.amount}
              onChange={(e) =>
                dispatch({
                  type: "UPDATE_OUTPUT_AMOUNT",
                  id: entry.id,
                  amount: parseFloat(e.target.value) || 0,
                })
              }
              className="w-24 bg-gray-800 text-gray-100 rounded px-2 py-1 text-sm"
              placeholder="/min"
            />
            <button
              type="button"
              aria-label="Remove output"
              onClick={() => dispatch({ type: "REMOVE_OUTPUT", id: entry.id })}
              className="text-gray-400 hover:text-red-400 text-xl leading-none flex-shrink-0"
            >
              ×
            </button>
          </div>
        ))}
      </div>
      {atLimit && (
        <p className="mt-1 text-xs text-yellow-400">Maximum of {MAX_OUTPUTS} outputs reached.</p>
      )}
      <button
        type="button"
        onClick={() => dispatch({ type: "ADD_OUTPUT" })}
        disabled={atLimit}
        className="mt-2 text-sm text-blue-400 hover:text-blue-300 disabled:text-gray-600 disabled:cursor-not-allowed"
      >
        + Add output
      </button>
    </section>
  );
}
