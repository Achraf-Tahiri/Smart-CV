import { describe, it, expect } from "vitest";

import { ROLE_LABELS, canUpload, canWrite, initials } from "./roles";

describe("roles — permissions", () => {
  it("canWrite : admin et recruteur autorisés, lecteur refusé", () => {
    expect(canWrite("admin")).toBe(true);
    expect(canWrite("recruteur")).toBe(true);
    expect(canWrite("lecteur")).toBe(false);
  });

  it("canUpload : admin et recruteur autorisés, lecteur refusé", () => {
    expect(canUpload("admin")).toBe(true);
    expect(canUpload("recruteur")).toBe(true);
    expect(canUpload("lecteur")).toBe(false);
  });
});

describe("roles — ROLE_LABELS", () => {
  it("libellés FR pour chaque rôle", () => {
    expect(ROLE_LABELS).toEqual({
      admin: "Administrateur",
      recruteur: "Recruteur",
      lecteur: "Lecteur",
    });
  });
});

describe("roles — initials", () => {
  it("prend les initiales du nom complet (2 lettres, majuscules)", () => {
    expect(initials("Marie Dupont", "marie@example.com")).toBe("MD");
  });

  it("se limite aux deux premiers mots", () => {
    expect(initials("Jean Pierre Martin", "x@y.z")).toBe("JP");
  });

  it("retombe sur l'email quand le nom est vide ou null (2 premiers tokens)", () => {
    expect(initials(null, "prenom@example.com")).toBe("PE");
    expect(initials("   ", "bob.smith@example.com")).toBe("BS");
  });

  it("découpe sur séparateurs variés de l'email", () => {
    expect(initials(null, "jean-luc@example.com")).toBe("JL");
  });
});
