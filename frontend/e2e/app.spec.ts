import { test, expect } from "@playwright/test";

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

test.describe("item dropdowns", () => {
  test("input dropdown is populated with game items", async ({ page }) => {
    await page.goto("/");
    await page.getByText(/\+ add input/i).click();

    const select = page.getByLabel("Input item");
    await expect(select).toBeVisible();

    const options = select.locator("option");
    const count = await options.count();
    expect(count).toBeGreaterThan(1); // more than just "Select item..."
  });

  test("output dropdown is populated with game items", async ({ page }) => {
    await page.goto("/");
    await page.getByText(/\+ add output/i).click();

    const select = page.getByLabel("Output item");
    await expect(select).toBeVisible();

    const options = select.locator("option");
    const count = await options.count();
    expect(count).toBeGreaterThan(1);
  });

  test("Iron Plate is available as an output", async ({ page }) => {
    await page.goto("/");
    await page.getByText(/\+ add output/i).click();

    const select = page.getByLabel("Output item");
    await expect(select.locator("option", { hasText: /^Iron Plate$/ })).toBeAttached();
  });
});

test.describe("solve flow", () => {
  test("Solve button is disabled with no outputs", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("button", { name: /solve/i })).toBeDisabled();
  });

  test("Solve button enables after selecting an output with a rate", async ({ page }) => {
    await page.goto("/");
    await page.getByText(/\+ add output/i).click();

    const select = page.getByLabel("Output item");
    await select.selectOption({ label: "Iron Plate" });

    const rateInput = page.getByLabel("Output rate per minute");
    await rateInput.fill("10");

    await expect(page.getByRole("button", { name: /solve/i })).toBeEnabled();
  });

  test("solving Iron Plate returns at least one result chain", async ({ page }) => {
    await page.goto("/");
    await page.getByText(/\+ add output/i).click();

    await page.getByLabel("Output item").selectOption({ label: "Iron Plate" });
    await page.getByLabel("Output rate per minute").fill("10");
    await page.getByRole("button", { name: /solve/i }).click();

    // Wait for the results count to appear, e.g. "(1 of 3)"
    await expect(page.getByText(/\(\d+ of \d+\)/)).toBeVisible({ timeout: 15000 });
  });
});
