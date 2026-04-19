import { useState, useRef } from "react";
import type { Item } from "../api/types";

interface Props {
  value: string;
  items: Item[];
  onChange: (item_class: string) => void;
  placeholder?: string;
  ariaLabel?: string;
}

export default function ItemCombobox({
  value,
  items,
  onChange,
  placeholder = "Select item…",
  ariaLabel,
}: Props) {
  const selectedItem = items.find((i) => i.class_name === value) ?? null;
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered =
    query.length === 0
      ? []
      : items.filter((i) => i.display_name.toLowerCase().includes(query.toLowerCase()));

  function handleFocus() {
    setQuery("");
    setOpen(true);
  }

  function handleBlur() {
    setQuery("");
    setOpen(false);
  }

  function handleSelect(item: Item) {
    onChange(item.class_name);
    setQuery("");
    setOpen(false);
    inputRef.current?.blur();
  }

  const displayValue = open ? query : (selectedItem?.display_name ?? "");

  return (
    <div className="relative flex-1 min-w-0">
      <input
        ref={inputRef}
        type="text"
        aria-label={ariaLabel}
        value={displayValue}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={handleFocus}
        onBlur={handleBlur}
        placeholder={open ? "Type to search…" : placeholder}
        autoComplete="off"
        className="w-full bg-gray-800 text-gray-100 rounded px-2 py-1 text-sm"
      />
      {open && (
        <ul className="absolute z-50 w-full mt-1 max-h-64 overflow-y-auto bg-gray-800 border border-gray-600 rounded shadow-lg">
          {filtered.length === 0 ? (
            <li className="px-2 py-1.5 text-sm text-gray-400 italic">
              {query.length === 0 ? "Start typing to search…" : "No matches"}
            </li>
          ) : (
            filtered.map((item) => (
              <li
                key={item.class_name}
                // pointerdown fires before blur, preventDefault keeps input focused
                // so the blur handler doesn't fire before onClick
                onPointerDown={(e) => e.preventDefault()}
                onClick={() => handleSelect(item)}
                className={`px-2 py-2 text-sm cursor-pointer hover:bg-gray-600 ${
                  item.class_name === value ? "bg-gray-700 text-blue-300" : "text-gray-100"
                }`}
              >
                {item.display_name}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
