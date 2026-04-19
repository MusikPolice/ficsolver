import { test, expect, type Page } from "@playwright/test";

/** Select an item via the searchable combobox. */
async function selectItem(page: Page, ariaLabel: string, displayName: string) {
  const input = page.getByLabel(ariaLabel);
  await input.fill(displayName);
  await page.getByRole("listitem").filter({ hasText: displayName }).first().click();
}

test.describe("page load", () => {
  test("shows app title", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "ficsolver" })).toBeVisible();
  });

  test("does not show data load error", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/failed to load game data/i)).not.toBeVisible();
  });

  test("loading indicator disappears after data loads", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/loading game data/i)).not.toBeVisible();
  });
});

test.describe("item comboboxes", () => {
  test("input combobox filters items by typed text", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.getByText(/\+ add input/i).click();

    const input = page.getByLabel("Input item");
    await expect(input).toBeVisible();
    await input.fill("iron");

    // At least one match should appear in the dropdown
    await expect(page.getByRole("listitem").first()).toBeVisible();
  });

  test("output combobox filters items by typed text", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.getByText(/\+ add output/i).click();

    const input = page.getByLabel("Output item");
    await expect(input).toBeVisible();
    await input.fill("iron");

    await expect(page.getByRole("listitem").first()).toBeVisible();
  });

  test("Iron Plate is available as an output", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.getByText(/\+ add output/i).click();

    await page.getByLabel("Output item").fill("Iron Plate");
    await expect(page.getByRole("listitem").filter({ hasText: /^Iron Plate$/ })).toBeVisible();
  });

  test("typing shows only matching items", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.getByText(/\+ add output/i).click();

    await page.getByLabel("Output item").fill("Wire");
    const items = page.getByRole("listitem");
    await expect(items.filter({ hasText: /^Wire$/ })).toBeVisible();
    await expect(items.filter({ hasText: /^Iron Plate$/ })).not.toBeVisible();
  });
});

test.describe("solve flow", () => {
  test("Solve button is disabled with no outputs", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("button", { name: /solve/i })).toBeDisabled();
  });

  test("Solve button enables after selecting an output with a rate", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.getByText(/\+ add output/i).click();

    await selectItem(page, "Output item", "Iron Plate");

    const rateInput = page.getByLabel("Output rate per minute");
    await rateInput.fill("10");

    await expect(page.getByRole("button", { name: /solve/i })).toBeEnabled();
  });

  test("solving Iron Plate returns at least one result chain", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.getByText(/\+ add output/i).click();

    await selectItem(page, "Output item", "Iron Plate");
    await page.getByLabel("Output rate per minute").fill("10");
    await page.getByRole("button", { name: /solve/i }).click();

    await expect(page.getByText(/\(\d+ of \d+\)/)).toBeVisible({ timeout: 15000 });
  });
});
