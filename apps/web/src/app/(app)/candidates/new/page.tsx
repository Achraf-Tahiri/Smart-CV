"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { useRequireAuth } from "@/app/providers";
import { CandidateForm } from "@/components/CandidateForm";
import { createCandidate, type CandidateInput } from "@/lib/api";
import { canWrite } from "@/lib/roles";
import { Card } from "@/components/ui/card";

export default function NewCandidatePage() {
  const { user } = useRequireAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  if (!user) return null;

  if (!canWrite(user.role)) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-foreground">Nouveau candidat</h1>
          <p className="mt-1 text-sm text-muted-foreground">Créer un nouveau profil candidat.</p>
        </div>
        <Card className="p-6">
          <p className="text-sm text-muted-foreground">Accès réservé aux recruteurs.</p>
        </Card>
      </div>
    );
  }

  async function onSubmit(data: CandidateInput) {
    setBusy(true);
    try {
      const created = await createCandidate(data);
      router.push(`/candidates/${created.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Échec de la création.");
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground">Nouveau candidat</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Renseignez les informations du candidat.
        </p>
      </div>
      <Card className="p-6">
        <CandidateForm onSubmit={onSubmit} submitLabel="Créer le candidat" busy={busy} />
      </Card>
    </div>
  );
}
