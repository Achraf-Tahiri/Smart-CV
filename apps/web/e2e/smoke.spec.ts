import { test, expect } from "@playwright/test";

// Compte de test seedé (configurable avec E2E_ADMIN_EMAIL et E2E_ADMIN_PASSWORD).
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "admin@example.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "password123";

// Parcours nominal : login → liste candidats → recherche par nom → fiche.
test("smoke : connexion, recherche d'un candidat et ouverture de sa fiche", async ({
  page,
}) => {
  // 1) Connexion.
  await page.goto("/login");
  await page.getByLabel("Adresse e-mail").fill(ADMIN_EMAIL);
  await page.getByLabel("Mot de passe", { exact: true }).fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);

  // 2) Liste des candidats (recherche initiale lancée au chargement).
  await page.goto("/candidates");
  await expect(
    page.getByRole("heading", { name: "Candidats", level: 1 }),
  ).toBeVisible();

  const firstRow = page.locator('ul li a[href^="/candidates/"]').first();
  await expect(firstRow).toBeVisible();

  const href = await firstRow.getAttribute("href");
  const fullName = (
    await firstRow.locator("span.font-semibold").first().innerText()
  ).trim();
  const token = fullName.split(/\s+/)[0];
  expect(href).toBeTruthy();
  expect(token.length).toBeGreaterThan(0);

  // 3) Recherche par nom → le candidat doit rester présent.
  await page.getByPlaceholder("Nom du candidat").fill(token);
  await page.getByRole("button", { name: "Rechercher" }).click();

  const targetLink = page.locator(`a[href="${href}"]`);
  await expect(targetLink).toBeVisible();

  // 4) Ouverture de la fiche → assertions clés.
  await targetLink.click();
  await expect(page).toHaveURL(new RegExp(`${href}$`));
  await expect(
    page.getByRole("link", { name: "Retour aux candidats" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: fullName, level: 1 }),
  ).toBeVisible();
});
