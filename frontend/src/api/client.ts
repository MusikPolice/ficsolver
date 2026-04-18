import type { Item, Recipe, ResultsParams, SolveRequest, SolveResponse } from "./types";

const API_BASE = "/api";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${response.status}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export async function getItems(): Promise<Item[]> {
  return fetchJson<Item[]>(`${API_BASE}/items`);
}

export async function getRecipes(): Promise<Recipe[]> {
  return fetchJson<Recipe[]>(`${API_BASE}/recipes`);
}

export async function postSolve(request: SolveRequest): Promise<SolveResponse> {
  return fetchJson<SolveResponse>(`${API_BASE}/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export async function getSolveResults(
  solveId: string,
  params: ResultsParams = {},
): Promise<SolveResponse> {
  const query = new URLSearchParams();
  if (params.sort !== undefined) query.set("sort", params.sort);
  if (params.page !== undefined) query.set("page", String(params.page));
  if (params.page_size !== undefined) query.set("page_size", String(params.page_size));
  const qs = query.toString();
  return fetchJson<SolveResponse>(
    `${API_BASE}/solve/${solveId}/results${qs ? `?${qs}` : ""}`,
  );
}
