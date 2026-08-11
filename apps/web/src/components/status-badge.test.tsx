import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { StatusBadge } from "./status-badge";

// Libellé FR + classes token attendus pour chaque statut connu.
const CASES: Array<{ status: string; label: string; bg: string }> = [
  { status: "pending", label: "En attente", bg: "bg-status-pending" },
  { status: "processing", label: "En traitement", bg: "bg-status-processing" },
  { status: "success", label: "Traité", bg: "bg-status-success" },
  { status: "manual_review", label: "À vérifier", bg: "bg-status-review" },
];

describe("StatusBadge", () => {
  it.each(CASES)(
    "affiche le libellé FR et les classes token pour '$status'",
    ({ status, label, bg }) => {
      render(<StatusBadge status={status} />);
      const badge = screen.getByText(label);
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass(bg);
      expect(badge).toHaveClass(`text-${bg.replace("bg-", "")}-foreground`);
    },
  );

  it("retombe sur un fallback propre pour un statut inconnu", () => {
    render(<StatusBadge status="n_importe_quoi" />);
    const badge = screen.getByText("Inconnu");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("bg-muted");
    expect(badge).toHaveClass("text-muted-foreground");
  });

  it("fusionne une className supplémentaire", () => {
    render(<StatusBadge status="success" className="ml-2" />);
    expect(screen.getByText("Traité")).toHaveClass("ml-2");
  });
});
