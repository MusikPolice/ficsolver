import { useState } from "react";
import type { ChainResultOut } from "../api/types";

interface Props {
  chain: ChainResultOut;
  /** Pre-computed fill width in percent (0–100). Worst chain across all displayed = 100. */
  barPct: number;
  itemNameMap: Map<string, string>;
}

function formatMachineClass(cls: string): string {
  return cls
    .replace(/^Build_/, "")
    .replace(/_C$/, "")
    .replace(/([a-z])([A-Z0-9])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2");
}

function fmt(n: number): string {
  const rounded = Math.round(n * 100) / 100;
  return rounded % 1 === 0 ? String(rounded) : rounded.toFixed(2).replace(/\.?0+$/, "");
}

export default function ChainCard({ chain, barPct, itemNameMap }: Props) {
  const [expanded, setExpanded] = useState(false);

  const budgetEntries = Object.values(chain.budget);
  const implicitEntries = Object.entries(chain.implicit_outputs);
  const cardKey = chain.machine_groups.map((g) => g.recipe_class).join(",");

  return (
    <article
      data-testid="chain-card"
      className={`bg-gray-800 rounded-lg border ${chain.has_deficit ? "border-amber-700" : "border-gray-700"}`}
    >
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        aria-label={`Chain with ${fmt(chain.total_resource_consumed)} resources per minute${chain.has_deficit ? ", budget deficit" : ""}. ${expanded ? "Collapse" : "Expand"} details.`}
        className="w-full text-left p-4"
      >
        {/* Resource bar */}
        <div className="flex items-center gap-2 mb-3">
          <div
            className="relative flex-1 h-2.5 bg-gray-700 rounded-full overflow-hidden"
            aria-hidden="true"
          >
            <div
              className={`absolute inset-y-0 left-0 rounded-full ${chain.has_deficit ? "bg-amber-500" : "bg-blue-500"}`}
              style={{ width: `${barPct}%` }}
            />
          </div>
          {chain.has_deficit && (
            <span aria-label="Budget deficit" className="text-amber-400 flex-shrink-0 text-sm">
              ⚠
            </span>
          )}
          <span className="text-xs text-gray-400 flex-shrink-0 tabular-nums">
            {fmt(chain.total_resource_consumed)} /min
          </span>
        </div>

        {/* Machine groups */}
        <ul className="space-y-0.5" aria-label="Machine groups">
          {chain.machine_groups.map((group) => (
            <li key={`${cardKey}-${group.recipe_class}`} className="text-sm flex justify-between gap-2">
              <span className="text-gray-200 min-w-0 truncate">{group.recipe_display_name}</span>
              <span className="text-gray-400 flex-shrink-0 tabular-nums">
                {group.machine_count}× {formatMachineClass(group.machine_class)} @{" "}
                {Math.ceil(group.clock_speed_pct)}%
              </span>
            </li>
          ))}
        </ul>

        {/* Implicit outputs */}
        {implicitEntries.length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-700">
            <p className="text-xs text-gray-500 mb-0.5">Side outputs:</p>
            <ul className="space-y-0.5">
              {implicitEntries.map(([cls, rate]) => (
                <li key={cls} className="text-xs text-gray-400">
                  {itemNameMap.get(cls) ?? cls}: {fmt(rate)} /min
                </li>
              ))}
            </ul>
          </div>
        )}

        <p className="text-xs text-gray-500 mt-2">
          {expanded ? "▲ Hide resource budget" : "▼ Show resource budget"}
        </p>
      </button>

      {/* Detail table — shown when expanded */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-700" data-testid="detail-table">
          {budgetEntries.length > 0 ? (
            <table className="w-full text-sm mt-3">
              <thead>
                <tr className="text-xs text-gray-500">
                  <th className="text-left pb-1 font-normal">Resource</th>
                  <th className="text-right pb-1 font-normal">Budget</th>
                  <th className="text-right pb-1 font-normal">Used</th>
                  <th className="text-right pb-1 font-normal">Delta</th>
                </tr>
              </thead>
              <tbody>
                {budgetEntries.map((entry) => {
                  const isDeficit = entry.delta < 0;
                  return (
                    <tr key={entry.item_class} className="border-t border-gray-700">
                      <td className="py-1.5 pr-2 text-gray-200">
                        {itemNameMap.get(entry.item_class) ?? entry.item_class}
                      </td>
                      <td className="text-right py-1.5 tabular-nums text-gray-400">
                        {entry.available > 0 ? fmt(entry.available) : "—"}
                      </td>
                      <td className="text-right py-1.5 tabular-nums text-gray-200">
                        {fmt(entry.consumed)}
                      </td>
                      <td
                        className={`text-right py-1.5 tabular-nums font-medium ${isDeficit ? "text-amber-400" : "text-green-400"}`}
                      >
                        {entry.delta >= 0 ? "+" : ""}
                        {fmt(entry.delta)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-gray-500 mt-3">No input budget declared.</p>
          )}
        </div>
      )}
    </article>
  );
}
