import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { searchCandidates, type Candidate } from "@/lib/api";
import CandidatesPage from "./page";

vi.mock("@/app/providers", () => {
  const user = { id: "demo-reader", role: "lecteur" };
  return { useRequireAuth: () => ({ user }) };
});
vi.mock("@/lib/api", () => ({ searchCandidates: vi.fn() }));

const candidates: Candidate[] = Array.from({ length: 31 }, (_, index) => ({
  id: `fictional-${index + 1}`,
  prenom: "Profil",
  nom: `Fictif ${index + 1}`,
  email: null,
  telephone: null,
  ville: null,
  poste_actuel: null,
  secteur: null,
  specialite: null,
  annees_experience: 0,
  experience_texte: null,
  seniorite: null,
  status: "success",
  source: "local",
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-01T00:00:00Z",
}));

beforeEach(() => {
  vi.mocked(searchCandidates).mockReset();
  vi.mocked(searchCandidates).mockImplementation(async ({ name, limit = 15, offset = 0 }) => {
    const filtered = candidates.filter((candidate) =>
      `${candidate.prenom} ${candidate.nom}`.includes(name ?? ""),
    );
    return { total: filtered.length, limit, offset, items: filtered.slice(offset, offset + limit) };
  });
});

describe("Pagination des candidats", () => {
  it("affiche 15 profils, navigue sans doublons et désactive les boutons aux extrémités", async () => {
    const user = userEvent.setup();
    render(<CandidatesPage />);
    await screen.findByText("1–15 sur 31 candidats");
    expect(screen.getAllByRole("listitem")).toHaveLength(15);
    expect(screen.getByRole("button", { name: /Précédent/ })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /Suivant/ }));
    await screen.findByText("16–30 sur 31 candidats");
    expect(screen.queryByText("Profil Fictif 15")).not.toBeInTheDocument();
    expect(screen.getByText("Profil Fictif 16")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(15);

    await user.click(screen.getByRole("button", { name: /Suivant/ }));
    await screen.findByText("Page 3 sur 3");
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByText("Profil Fictif 31")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Suivant/ })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /Précédent/ }));
    await screen.findByText("16–30 sur 31 candidats");
    expect(searchCandidates).toHaveBeenLastCalledWith(expect.objectContaining({ limit: 15, offset: 15 }));
  });

  it("revient à la première page après une recherche et gère les résultats vides", async () => {
    const user = userEvent.setup();
    render(<CandidatesPage />);
    await screen.findByText("Page 1 sur 3");
    await user.click(screen.getByRole("button", { name: /Suivant/ }));
    await screen.findByText("Page 2 sur 3");

    await user.type(screen.getByLabelText("Nom du candidat"), "Fictif 31");
    await user.click(screen.getByRole("button", { name: "Rechercher" }));
    await screen.findByText("1–1 sur 1 candidat");
    expect(searchCandidates).toHaveBeenLastCalledWith(expect.objectContaining({ limit: 15, offset: 0, name: "Fictif 31" }));
    expect(screen.queryByRole("navigation", { name: "Pagination des candidats" })).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("Nom du candidat"), " absent");
    await user.click(screen.getByRole("button", { name: "Rechercher" }));
    await screen.findByText("Aucun résultat");
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });
});
