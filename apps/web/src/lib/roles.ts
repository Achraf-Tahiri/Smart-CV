// Libellés et permissions dérivés du rôle (auth existante — voir lib/api.ts).
import type { Role } from "@/lib/api";

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Administrateur",
  recruteur: "Recruteur",
  lecteur: "Lecteur",
};

/** Import de CV réservé aux recruteurs et administrateurs. */
export function canUpload(role: Role): boolean {
  return role === "admin" || role === "recruteur";
}

/** Écriture (création/édition) réservée aux recruteurs et administrateurs. */
export function canWrite(role: Role): boolean {
  return role === "admin" || role === "recruteur";
}

/** Initiales pour l'avatar : à partir du nom complet, sinon de l'email. */
export function initials(fullName: string | null, email: string): string {
  const source = (fullName ?? "").trim() || email;
  const parts = source.split(/[\s@._-]+/).filter(Boolean);
  const letters = parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "");
  return letters.join("") || email[0]?.toUpperCase() || "?";
}
