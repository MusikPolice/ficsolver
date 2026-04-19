import { useState } from "react";
import type { ChainResultOut, SolveFailureOut, SolveResponse } from "../api/types";
import type { SortKey } from "../state";
import ChainCard from "./ChainCard";

interface Props {
  response: SolveResponse;
  displayedResults: ChainResultOut[];
  isLoadingMore: boolean;
  currentSort: SortKey;
  itemNameMap: Map<string, string>;
  onLoadMore: () => void;
  onSortChange: (sort: SortKey) => void;
}

function Phase1FailureCard({ failure }: { failure: SolveFailureOut }) {
  return (
    <div role="alert" data-testid="phase1-failure" className="bg-gray-800 border border-red-700 rounded-lg p-4">
      <p className="font-semibold text-red-400">✕ No recipe path found</p>
      <p className="text-sm text-gray-300 mt-1">{failure.message}</p>
    </div>
  );
}

function Phase2FailureCard({
  failure,
  itemNameMap,
}: {
  failure: SolveFailureOut;
  itemNameMap: Map<string, string>;
}) {
  const [expanded, setExpanded] = useState(false);
  const deficits = failure.chain_deficits ?? [];

  return (
    <div role="alert" data-testid="phase2-failure" className="bg-gray-800 border border-amber-700 rounded-lg">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        className="w-full text-left p-4"
      >
        <p className="font-semibold text-amber-400">⚠ No viable chains found</p>
        <p className="text-sm text-gray-300 mt-1">
          All paths require undeclared inputs. Add the missing resources to your inputs and
          re-solve.
        </p>
        {deficits.length > 0 && (
          <p className="text-xs text-gray-500 mt-2">
            {expanded ? "▲ Hide per-chain breakdown" : "▼ Show per-chain breakdown"}
          </p>
        )}
      </button>

      {expanded && deficits.length > 0 && (
        <div
          className="px-4 pb-4 border-t border-gray-700 space-y-3 mt-1"
          data-testid="chain-deficits"
        >
          {deficits.map((chainDeficit, i) => (
            <div key={i}>
              <p className="text-xs text-gray-500 mb-1 pt-3">Chain {i + 1} missing:</p>
              <ul className="space-y-0.5">
                {Object.entries(chainDeficit).map(([cls, rate]) => (
                  <li key={cls} className="text-sm text-amber-300">
                    {itemNameMap.get(cls) ?? cls}: {rate.toFixed(2)} /min
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ResultsView({
  response,
  displayedResults,
  isLoadingMore,
  currentSort,
  itemNameMap,
  onLoadMore,
  onSortChange,
}: Props) {
  const hasMore =
    response.solve_id !== null && displayedResults.length < response.total_count;

  const maxConsumed = Math.max(
    1,
    ...displayedResults.map((r) => r.total_resource_consumed),
  );

  return (
    <section aria-label="Solver Results" className="space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
          Results
          {response.total_count > 0 && (
            <span className="ml-2 text-gray-500 normal-case font-normal">
              ({displayedResults.length} of {response.total_count})
            </span>
          )}
        </h2>
        {!response.failure && response.total_count > 0 && (
          <div className="flex items-center gap-2">
            <label htmlFor="sort-select" className="text-xs text-gray-500">
              Sort:
            </label>
            <select
              id="sort-select"
              value={currentSort}
              onChange={(e) => {
                onSortChange(e.target.value as SortKey);
              }}
              className="bg-gray-800 text-gray-200 text-sm rounded px-2 py-0.5 border border-gray-700"
            >
              <option value="resource">Resource use</option>
            </select>
          </div>
        )}
      </div>

      {/* Cap-reached notice */}
      {response.cap_reached && (
        <div
          role="status"
          data-testid="cap-reached-notice"
          className="text-xs text-yellow-400 bg-yellow-900/30 border border-yellow-700 rounded px-3 py-2"
        >
          Result set may be incomplete — the solver reached its chain limit. Consider narrowing
          your alternate recipe selection.
        </div>
      )}

      {/* Failure states */}
      {response.failure ? (
        response.failure.failure_type === "phase1" ? (
          <Phase1FailureCard failure={response.failure} />
        ) : (
          <Phase2FailureCard failure={response.failure} itemNameMap={itemNameMap} />
        )
      ) : (
        <>
          {/* All-chains-deficit banner (chains exist but all have deficits) */}
          {response.all_chains_have_deficit && (
            <div
              role="status"
              data-testid="all-deficit-notice"
              className="text-xs text-amber-400 bg-amber-900/30 border border-amber-700 rounded px-3 py-2"
            >
              ⚠ All chains exceed your input budget. Add more inputs or choose a different recipe
              path.
            </div>
          )}

          {/* Chain cards */}
          <div className="space-y-3">
            {displayedResults.map((chain) => {
              const key = chain.machine_groups.map((g) => g.recipe_class).join(",") || String(Math.random());
              return (
                <ChainCard
                  key={key}
                  chain={chain}
                  barPct={(chain.total_resource_consumed / maxConsumed) * 100}
                  itemNameMap={itemNameMap}
                />
              );
            })}
          </div>

          {/* Load more */}
          {hasMore && (
            <button
              type="button"
              onClick={onLoadMore}
              disabled={isLoadingMore}
              data-testid="load-more-button"
              className="w-full py-2 text-sm bg-gray-800 hover:bg-gray-700 disabled:text-gray-500 rounded border border-gray-700 transition-colors"
            >
              {isLoadingMore
                ? "Loading…"
                : `Load more (${response.total_count - displayedResults.length} remaining)`}
            </button>
          )}
        </>
      )}
    </section>
  );
}
