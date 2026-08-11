import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CandidateForm } from "./CandidateForm";

// pointerEventsCheck: 0 → Radix Select (portal + pointer capture) fonctionne sous jsdom.
function setup() {
  const onSubmit = vi.fn();
  const user = userEvent.setup({ pointerEventsCheck: 0 });
  render(<CandidateForm onSubmit={onSubmit} submitLabel="Enregistrer" />);
  return { onSubmit, user };
}

// Radix Select : ordre DOM des triggers = [secteur, seniorité, statut].
function comboboxes() {
  return screen.getAllByRole("combobox");
}

async function pickOption(
  user: ReturnType<typeof userEvent.setup>,
  trigger: HTMLElement,
  optionName: string | RegExp,
) {
  await user.click(trigger);
  const listbox = await screen.findByRole("listbox");
  await user.click(within(listbox).getByRole("option", { name: optionName }));
}

describe("CandidateForm — rendu", () => {
  it("affiche les 3 sections Identité / Coordonnées / Profil", () => {
    render(<CandidateForm onSubmit={vi.fn()} submitLabel="Enregistrer" />);
    expect(screen.getByText("Identité")).toBeInTheDocument();
    expect(screen.getByText("Coordonnées")).toBeInTheDocument();
    expect(screen.getByText("Profil")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Enregistrer" }),
    ).toBeInTheDocument();
  });
});

describe("CandidateForm — soumission", () => {
  it("soumet le payload avec les champs texte saisis (via user-event)", async () => {
    const { onSubmit, user } = setup();

    await user.type(screen.getByLabelText("Prénom"), "Marie");
    await user.type(screen.getByLabelText("Nom"), "Dupont");
    await user.type(screen.getByLabelText("Email"), "marie@example.com");
    await user.type(screen.getByLabelText("Ville"), "Casablanca");

    await user.click(screen.getByRole("button", { name: "Enregistrer" }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        prenom: "Marie",
        nom: "Dupont",
        email: "marie@example.com",
        ville: "Casablanca",
      }),
    );
  });

  it("valeurs par défaut : sentinel __none__ → chaîne vide, statut 'success', exp 0", async () => {
    const { onSubmit, user } = setup();

    await user.click(screen.getByRole("button", { name: "Enregistrer" }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const payload = onSubmit.mock.calls[0][0];
    // Selects optionnels non touchés : le sentinel __none__ est remappé en "".
    expect(payload.secteur).toBe("");
    expect(payload.seniorite).toBe("");
    expect(payload.status).toBe("success");
    expect(payload.annees_experience).toBe(0);
  });

  it("mappe les Select : secteur choisi, séniorité choisie, statut changé", async () => {
    const { onSubmit, user } = setup();
    const [secteur, seniorite, statut] = comboboxes();

    await pickOption(user, secteur, "Informatique / Tech");
    await pickOption(user, seniorite, "Senior");
    await pickOption(user, statut, "À vérifier");

    await user.click(screen.getByRole("button", { name: "Enregistrer" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        secteur: "Informatique / Tech",
        seniorite: "Senior",
        status: "manual_review",
      }),
    );
  });
});
