import type { Dispatch } from "react";
import type { Recipe } from "../api/types";
import type { Action } from "../state";

interface Props {
  alternates: Recipe[];
  unlockedAlternates: string[];
  dispatch: Dispatch<Action>;
}

export default function AlternatesPanel({ alternates, unlockedAlternates, dispatch }: Props) {
  if (alternates.length === 0) {
    return (
      <section aria-label="Alternate Recipes">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Alternate Recipes
        </h2>
        <p className="text-sm text-gray-500">
          Select desired outputs to see relevant alternate recipes.
        </p>
      </section>
    );
  }

  return (
    <section aria-label="Alternate Recipes">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2">
        Alternate Recipes
      </h2>
      <div className="space-y-1">
        {alternates.map((recipe) => {
          const checked = unlockedAlternates.includes(recipe.class_name);
          return (
            <label key={recipe.class_name} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={checked}
                onChange={() =>
                  dispatch({ type: "TOGGLE_ALTERNATE", class_name: recipe.class_name })
                }
                className="accent-blue-500"
              />
              <span className="text-sm text-gray-200">{recipe.display_name.replace(/^Alternate:\s*/i, "")}</span>
            </label>
          );
        })}
      </div>
    </section>
  );
}
