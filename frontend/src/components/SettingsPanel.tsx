import type { Dispatch } from "react";
import type { Action } from "../state";

interface Props {
  clockingAvailable: boolean;
  excludeConverterRecipes: boolean;
  dispatch: Dispatch<Action>;
}

export default function SettingsPanel({ clockingAvailable, excludeConverterRecipes, dispatch }: Props) {
  return (
    <section aria-label="Settings">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Settings
      </h2>
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={clockingAvailable}
          onChange={(e) => dispatch({ type: "SET_CLOCKING", value: e.target.checked })}
          className="accent-blue-500"
        />
        <span className="text-sm text-gray-200">Clocking available</span>
      </label>
      <p className="mt-1 text-xs text-gray-500">
        When disabled, all machines are reported at 100% clock speed.
      </p>
      <label className="flex items-center gap-2 cursor-pointer mt-3">
        <input
          type="checkbox"
          checked={excludeConverterRecipes}
          onChange={(e) => dispatch({ type: "SET_EXCLUDE_CONVERTER", value: e.target.checked })}
          className="accent-blue-500"
        />
        <span className="text-sm text-gray-200">Exclude Converter recipes</span>
      </label>
      <p className="mt-1 text-xs text-gray-500">
        Hides solutions that use the Converter building to produce resources from Reanimated SAM.
      </p>
    </section>
  );
}
