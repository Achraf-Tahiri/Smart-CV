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
  for (const viewport of [
    { width: 1024, height: 600 },
    { width: 1920, height: 1080 },
    { width: 2560, height: 1440 },
    { width: 1440, height: 900 },
  ]) {
    await page.setViewportSize(viewport);
    const layout = await page.evaluate(() => {
      const sidebar = document.querySelector("aside").getBoundingClientRect();
      const content = document.querySelector("main > div:last-child").getBoundingClientRect();
      return {
        sidebarHeight: sidebar.height,
        sidebarWidth: sidebar.width,
        contentLeft: content.left,
        sidebarRight: sidebar.right,
        contentRight: content.right,
        pageWidth: document.documentElement.scrollWidth,
      };
    });
    assert.ok(layout.sidebarHeight >= viewport.height, "Sidebar must fill the screen height");
    assert.ok(Math.abs(layout.sidebarWidth - Math.max(256, viewport.width * 0.2)) < 1,
      "Sidebar width must grow with the viewport");
    assert.equal(layout.contentLeft, layout.sidebarRight, "Content must start beside the sidebar");
    assert.equal(layout.contentRight, viewport.width, "Content must use the available width");
    assert.equal(layout.pageWidth, viewport.width, "Desktop layout must not overflow horizontally");
  }
  await page.screenshot({ path: `${output}/dashboard.png`, animations: "disabled" });
  await page.goto(`${base}/candidates`);
  await page.getByText("Camille Exemple", { exact: true }).waitFor();
  // Effective CSS viewports for a 1920×1080 screen at 50%–400% browser zoom,
  // plus a short desktop window to exercise independent navigation scrolling.
  for (const viewport of [
    { width: 3840, height: 2160 },
    { width: 1920, height: 1080 },
    { width: 1536, height: 864 },
    { width: 1280, height: 720 },
    { width: 1024, height: 576 },
    { width: 960, height: 540 },
    { width: 640, height: 360 },
    { width: 480, height: 270 },
    { width: 320, height: 216 },
    { width: 1024, height: 200 },
  ]) {
    await page.setViewportSize(viewport);
    for (const fraction of [0, 0.5, 1]) {
      await page.evaluate((fraction) => window.scrollTo(0,
        fraction * (document.documentElement.scrollHeight - innerHeight)), fraction);
      const mobile = viewport.width < 1024;
      if (mobile) await page.getByRole("button", { name: "Ouvrir le menu", exact: true }).click();
      const panel = mobile ? page.getByRole("dialog") : page.locator("aside");
      const account = panel.getByRole("button", { name: /Compte de démonstration/ });
      await expect(account).toBeInViewport({ ratio: 1 });
      const bounds = await account.boundingBox();
      assert.ok(bounds && bounds.y >= 0 && bounds.y + bounds.height <= viewport.height,
        `Account must stay inside the viewport at ${viewport.width}×${viewport.height}, scroll ${fraction}`);
      await account.click();
      await expect(page.getByRole("menuitem", { name: "Se déconnecter" })).toBeInViewport();
      await page.keyboard.press("Escape");
      if (mobile) await panel.getByRole("button", { name: "Fermer", exact: true }).click();
    }
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true,
      "Candidates page must not overflow horizontally at zoomed viewport sizes");
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: `${output}/candidates.png`, animations: "disabled" });
  await page.setViewportSize({ width: 1920, height: 1080 });
  const wideSidebar = await page.locator("aside").boundingBox();
  assert.ok(wideSidebar && Math.abs(wideSidebar.width - 384) < 1);
  await page.screenshot({ path: `${output}/candidates-wide.png`, animations: "disabled" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.getByPlaceholder("Nom du candidat").fill("Camille");
  await page.getByRole("button", { name: "Rechercher", exact: true }).click();
  await page.getByText("Alex Démo", { exact: true }).waitFor({ state: "hidden" });
  await page.getByText("Camille Exemple", { exact: true }).click();
  await page.getByRole("heading", { name: "Camille Exemple", exact: true }).waitFor();
  await page.getByText("candidate-01@example.com", { exact: true }).waitFor();
  assert.equal(await page.locator("aside").evaluate((sidebar) =>
    sidebar.getBoundingClientRect().bottom >= document.documentElement.scrollHeight,
  ), true, "Sidebar background must extend to the bottom of a long page");
  await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
  const navigation = await page.locator("aside nav").boundingBox();
  assert.ok(navigation && navigation.y >= 0 && navigation.y + navigation.height <= 900,
    "Desktop navigation must remain visible after scrolling");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: `${output}/candidate-profile.png`, animations: "disabled" });
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
  console.log("Captured six screenshots; verified synthetic data, search, profile navigation, read-only access, desktop resizing, account visibility while scrolling, zoom-equivalent viewports, and mobile layout.");
} catch (error) {
  if (page) { console.error("Capture failed at", page.url(), await page.locator("body").innerText()); }
  throw error;
} finally {
  await browser.close();
}
