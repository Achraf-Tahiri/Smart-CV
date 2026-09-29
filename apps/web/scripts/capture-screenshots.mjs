/** Capture the real UI against the isolated synthetic preview only. */
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { chromium, expect } from "@playwright/test";

const base = "http://127.0.0.1:3105";
const api = "http://127.0.0.1:8105";
const output = fileURLToPath(new URL("../../../docs/images/", import.meta.url));
const health = await fetch(`${api}/health`).then((response) => response.json());
assert.equal(health.mode, "synthetic-preview", "Refusing to capture a non-demo backend");
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined,
  headless: true,
});
let page;
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, colorScheme: "light" });
  const blocked = [];
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if ([base, api].includes(url.origin)) return route.continue();
    blocked.push(url.origin);
    return route.abort();
  });
  page = await context.newPage();
  page.on("console", (message) => { if (message.type() === "error") console.error(message.text()); });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`${base}/login`);
  await page.getByRole("heading", { name: "Connexion", exact: true }).waitFor();
  await page.screenshot({ path: `${output}/login.png`, animations: "disabled" });
  await page.getByLabel("Adresse e-mail").fill("demo@example.com");
  await page.getByLabel("Mot de passe", { exact: true }).fill("demo-only");
  await page.getByRole("button", { name: "Se connecter", exact: true }).click();
  await expect(page).toHaveURL(`${base}/dashboard`, { timeout: 45000 });
  await page.getByText("Candidats au total", { exact: true }).waitFor();
  await page.getByRole("note").filter({ hasText: "Données entièrement fictives" }).waitFor();
  const kpi = page.getByText("Candidats au total", { exact: true }).locator("..");
  assert.match(await kpi.innerText(), /8/);
  await page.screenshot({ path: `${output}/dashboard.png`, animations: "disabled" });
  await page.goto(`${base}/candidates`);
  await page.getByText("Camille Exemple", { exact: true }).waitFor();
  await page.screenshot({ path: `${output}/candidates.png`, animations: "disabled", fullPage: true });
  await page.getByPlaceholder("Nom du candidat").fill("Camille");
  await page.getByRole("button", { name: "Rechercher", exact: true }).click();
  await page.getByText("Alex Démo", { exact: true }).waitFor({ state: "hidden" });
  await page.getByText("Camille Exemple", { exact: true }).click();
  await page.getByRole("heading", { name: "Camille Exemple", exact: true }).waitFor();
  await page.getByText("candidate-01@example.com", { exact: true }).waitFor();
  await page.screenshot({ path: `${output}/candidate-profile.png`, animations: "disabled", fullPage: true });
  assert.equal(await page.getByRole("button", { name: "Supprimer", exact: true }).count(), 0, "Preview must remain read-only");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${base}/dashboard`);
  await page.getByText("Candidats au total", { exact: true }).waitFor();
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await page.getByRole("button", { name: "Ouvrir le menu", exact: true }).click();
  await page.getByRole("dialog").waitFor();
  await page.screenshot({ path: `${output}/mobile.png`, animations: "disabled" });
  assert.deepEqual(blocked, [], "Unexpected network destination during capture");
  assert.deepEqual(errors, [], "Browser errors during preview");
  console.log("Captured five screenshots; verified synthetic data, search, profile navigation, read-only access, and mobile layout.");
} catch (error) {
  if (page) { console.error("Capture failed at", page.url(), await page.locator("body").innerText()); }
  throw error;
} finally {
  await browser.close();
}
