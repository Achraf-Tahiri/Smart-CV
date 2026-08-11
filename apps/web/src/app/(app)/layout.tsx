"use client";

import type { ReactNode } from "react";

import { useRequireAuth } from "@/app/providers";
import { AppShell } from "@/components/app-shell/app-shell";

// Enveloppe l'espace applicatif dans le shell (sidebar + header) et garantit
// l'authentification (redirige vers /login si besoin). Les pages internes
// restent inchangées ; seul l'habillage change.
export default function AppLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useRequireAuth();

  if (loading || !user) return null;

  return <AppShell>{children}</AppShell>;
}
