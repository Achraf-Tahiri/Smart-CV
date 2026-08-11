"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useRequireAuth } from "@/app/providers";
import { CandidateForm } from "@/components/CandidateForm";
import { getCandidate, updateCandidate, type CandidateDetail, type CandidateInput } from "@/lib/api";
import { canWrite } from "@/lib/roles";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

function FormSkeleton() {
  return (
    <div className="space-y-8">
      {[1, 2, 3].map((i) => (
        <div key={i} className="space-y-4">
          <Skeleton className="h-3 w-20" />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Skeleton className="h-9" />
            <Skeleton className="h-9" />
          </div>
        </div>
      ))}
      <Skeleton className="h-9 w-36" />
    </div>
  );
}

export default function EditCandidatePage() {
  const { user } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    getCandidate(id)
      .then(setCandidate)
      .catch((err) =>
        toast.error(
          err instanceof Error ? err.message : "Impossible de charger le candidat.",
        ),
      );
  }, [user, id]);

  if (!user) return null;

  if (!canWrite(user.role)) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-foreground">Modifier le candidat</h1>
          <p className="mt-1 text-sm text-muted-foreground">Mise à jour du profil candidat.</p>
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
      await updateCandidate(id, data);
      router.push(`/candidates/${id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Échec de la mise à jour.");
      setBusy(false);
    }
  }

  const candidateName = candidate
    ? [candidate.prenom, candidate.nom].filter(Boolean).join(" ") || "le candidat"
    : "le candidat";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground">
          Modifier {candidateName}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Mettez à jour les informations du candidat.
        </p>
      </div>
      <Card className="p-6">
        {!candidate ? (
          <FormSkeleton />
        ) : (
          <CandidateForm
            initial={candidate}
            onSubmit={onSubmit}
            submitLabel="Enregistrer"
            busy={busy}
          />
        )}
      </Card>
    </div>
  );
}
