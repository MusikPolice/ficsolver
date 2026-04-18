import { useEffect, useReducer } from "react";
import { getItems, getRecipes, postSolve } from "./api/client";
import AlternatesPanel from "./components/AlternatesPanel";
import InputsPanel from "./components/InputsPanel";
import OutputsPanel from "./components/OutputsPanel";
import SettingsPanel from "./components/SettingsPanel";
import { initialState, reducer, relevantAlternates } from "./state";

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    Promise.all([getItems(), getRecipes()])
      .then(([items, recipes]) => {
        dispatch({ type: "SET_ITEMS", items });
        dispatch({ type: "SET_RECIPES", recipes });
      })
      .catch((err: unknown) => {
        dispatch({ type: "DATA_ERROR", error: String(err) });
      });
  }, []);

  async function handleSolve() {
    const outputs: Record<string, number> = {};
    for (const o of state.outputs) {
      if (o.item_class && o.amount > 0) outputs[o.item_class] = o.amount;
    }
    if (Object.keys(outputs).length === 0) return;

    const inputs: Record<string, number> = {};
    for (const i of state.inputs) {
      if (i.item_class && i.amount > 0) inputs[i.item_class] = i.amount;
    }

    dispatch({ type: "SOLVE_START" });
    try {
      const result = await postSolve({
        inputs: Object.keys(inputs).length > 0 ? inputs : undefined,
        outputs,
        unlocked_alternates: state.unlockedAlternates,
        clocking_available: state.clockingAvailable,
      });
      dispatch({ type: "SOLVE_SUCCESS", result });
    } catch (err: unknown) {
      dispatch({ type: "SOLVE_ERROR", error: String(err) });
    }
  }

  const alternates = relevantAlternates(state.outputs, state.recipes);
  const canSolve = state.outputs.some((o) => o.item_class && o.amount > 0);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="px-4 py-3 border-b border-gray-800">
        <h1 className="text-lg font-bold">ficsolver</h1>
      </header>
      <main className="max-w-2xl mx-auto px-4 py-4 space-y-6">
        {state.dataLoading && (
          <p className="text-sm text-gray-400">Loading game data…</p>
        )}
        {state.dataError && (
          <p className="text-sm text-red-400">Failed to load game data: {state.dataError}</p>
        )}
        <SettingsPanel clockingAvailable={state.clockingAvailable} dispatch={dispatch} />
        <InputsPanel inputs={state.inputs} items={state.items} dispatch={dispatch} />
        <OutputsPanel outputs={state.outputs} items={state.items} dispatch={dispatch} />
        <AlternatesPanel
          alternates={alternates}
          unlockedAlternates={state.unlockedAlternates}
          dispatch={dispatch}
        />
        <button
          type="button"
          onClick={() => void handleSolve()}
          disabled={state.solverStatus === "loading" || !canSolve}
          className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 rounded font-semibold transition-colors"
        >
          {state.solverStatus === "loading" ? "Solving…" : "Solve"}
        </button>
        {state.solverStatus === "error" && state.solveError && (
          <p className="text-sm text-red-400">Solve failed: {state.solveError}</p>
        )}
      </main>
    </div>
  );
}
