"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  ArrowLeft,
  Briefcase,
  Building2,
  Clock,
  Download,
  FileText,
  GraduationCap,
  Mail,
  MapPin,
  Phone,
  Zap,
} from "lucide-react";

import { useRequireAuth } from "@/app/providers";
import {
  deleteCandidate,
  getCandidate,
  getDownloadUrl,
  type Activity,
  type CandidateDetail,
  type Experience,
} from "@/lib/api";
import { canWrite } from "@/lib/roles";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function month(value: string | null): string {
  return value ? value.slice(0, 7) : "?";
}

function period(item: {
  date_debut: string | null;
  date_fin: string | null;
  is_current: boolean;
}) {
  const fin = item.is_current ? "présent" : month(item.date_fin);
  return `${month(item.date_debut)} → ${fin}`;
}

function candidateInitials(c: CandidateDetail): string {
  const p = c.prenom?.trim()[0]?.toUpperCase() ?? "";
  const n = c.nom?.trim()[0]?.toUpperCase() ?? "";
  return p + n || "?";
}

function candidateName(c: CandidateDetail): string {
  return [c.prenom, c.nom].filter(Boolean).join(" ") || "(Sans nom)";
}

// ─── Skeleton de chargement ────────────────────────────────────────────────────

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-4 w-44" />
      <div className="rounded-xl border bg-card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <Skeleton className="size-16 rounded-xl" />
            <div className="space-y-2">
              <Skeleton className="h-7 w-52" />
              <Skeleton className="h-4 w-60" />
              <Skeleton className="h-5 w-24 rounded-full" />
            </div>
          </div>
          <div className="flex gap-2">
            <Skeleton className="h-8 w-24 rounded-md" />
            <Skeleton className="h-8 w-28 rounded-md" />
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Skeleton className="h-44 rounded-xl" />
          <Skeleton className="h-28 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
        </div>
        <div className="space-y-6">
          <Skeleton className="h-36 rounded-xl" />
          <Skeleton className="h-28 rounded-xl" />
          <Skeleton className="h-20 rounded-xl" />
          <Skeleton className="h-28 rounded-xl" />
        </div>
      </div>
    </div>
  );
}

// ─── Bloc de section ──────────────────────────────────────────────────────────

function SectionCard({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("p-5", className)}>
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      {children}
    </Card>
  );
}

// ─── Ligne d'info (coordonnées) ───────────────────────────────────────────────

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string | null | undefined;
}) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-3 text-sm">
      <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="break-words font-medium text-foreground">{value}</p>
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function CandidateDetailPage() {
  const { user } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  useEffect(() => {
    if (!user) return;
    getCandidate(id)
      .then(setCandidate)
      .catch((err) => setError(err instanceof Error ? err.message : "Erreur."))
      .finally(() => setLoading(false));
  }, [user, id]);

  async function download(documentId: string) {
    try {
      const { url } = await getDownloadUrl(documentId);
      window.open(url, "_blank");
    } catch {
      toast.error("Téléchargement impossible.");
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteCandidate(id);
      router.push("/candidates");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Suppression impossible.");
      setDeleting(false);
      setDeleteOpen(false);
    }
  }

  if (!user) return null;
  const write = canWrite(user.role);

  if (loading) return <PageSkeleton />;

  return (
    <div className="space-y-6">
      {/* Lien retour */}
      <Link
        href="/candidates"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Retour aux candidats
      </Link>

      {error && (
        <p className="rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </p>
      )}

      {candidate && (
        <>
          {/* ── En-tête ─────────────────────────────────────────── */}
          <Card className="p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              {/* Identité */}
              <div className="flex items-center gap-4">
                <Avatar className="size-16 rounded-xl">
                  <AvatarFallback className="rounded-xl bg-primary/10 text-xl font-semibold text-primary">
                    {candidateInitials(candidate)}
                  </AvatarFallback>
                </Avatar>
                <div className="space-y-1">
                  <h1 className="font-display text-2xl font-bold text-foreground">
                    {candidateName(candidate)}
                  </h1>
                  {(candidate.poste_actuel || candidate.seniorite) && (
                    <p className="text-sm text-muted-foreground">
                      {[candidate.poste_actuel, candidate.seniorite]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  )}
                  <StatusBadge status={candidate.status} />
                </div>
              </div>

              {/* Boutons d'action */}
              {write && (
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/candidates/${id}/edit`}>Modifier</Link>
                  </Button>

                  <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
                    <AlertDialogTrigger asChild>
                      <Button variant="destructive" size="sm">
                        Supprimer
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Supprimer ce candidat ?</AlertDialogTitle>
                        <AlertDialogDescription>
                          Cette action est irréversible. Elle supprime
                          définitivement{" "}
                          <strong>{candidateName(candidate)}</strong> et toutes
                          ses données : expériences, compétences, langues,
                          documents…
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel disabled={deleting}>
                          Annuler
                        </AlertDialogCancel>
                        <Button
                          variant="destructive"
                          disabled={deleting}
                          onClick={handleDelete}
                        >
                          {deleting ? "Suppression…" : "Supprimer définitivement"}
                        </Button>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              )}
            </div>
          </Card>

          {/* ── Corps 2 colonnes ────────────────────────────────── */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

            {/* Colonne principale */}
            <div className="space-y-6 lg:col-span-2">

              {/* Expériences — timeline */}
              {candidate.experiences.length > 0 && (
                <SectionCard title="Expériences professionnelles">
                  <ul className="relative space-y-5 pl-6">
                    {/* Filet vertical */}
                    <span
                      aria-hidden
                      className="absolute left-2.5 top-1 bottom-0 w-px bg-primary/20"
                    />
                    {candidate.experiences.map((e: Experience) => (
                      <li key={e.id} className="relative">
                        {/* Dot sur le filet */}
                        <span
                          aria-hidden
                          className="absolute left-1.5 top-2 size-2 rounded-full bg-primary/60 ring-2 ring-card"
                        />
                        <div className="text-sm font-semibold text-foreground">
                          {e.poste || "Poste non renseigné"}
                        </div>
                        {e.entreprise && (
                          <div className="text-sm text-muted-foreground">
                            {e.entreprise}
                          </div>
                        )}
                        <div className="mt-0.5 text-xs text-muted-foreground/70">
                          {period(e)}
                        </div>
                        {e.description && (
                          <p className="mt-2 text-sm text-muted-foreground">
                            {e.description}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                </SectionCard>
              )}

              {/* Formations */}
              {candidate.educations.length > 0 && (
                <SectionCard title="Formations">
                  <ul className="space-y-4">
                    {candidate.educations.map((f) => (
                      <li key={f.id} className="flex items-start gap-3">
                        <GraduationCap className="mt-0.5 size-4 shrink-0 text-primary/60" />
                        <div className="text-sm">
                          <div className="font-semibold text-foreground">
                            {f.diplome || "Diplôme"}
                          </div>
                          {f.ecole && (
                            <div className="text-muted-foreground">{f.ecole}</div>
                          )}
                          {f.annee && (
                            <div className="text-xs text-muted-foreground/70">
                              {f.annee}
                            </div>
                          )}
                          {f.description && (
                            <p className="mt-1 text-muted-foreground">
                              {f.description}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </SectionCard>
              )}

              {/* Activités extra-professionnelles */}
              {candidate.activites_extra.length > 0 && (
                <SectionCard title="Activités extra-professionnelles">
                  <ul className="space-y-4">
                    {candidate.activites_extra.map((a: Activity) => (
                      <li key={a.id} className="flex items-start gap-3">
                        <Zap className="mt-0.5 size-4 shrink-0 text-primary/60" />
                        <div className="text-sm">
                          <div className="font-semibold text-foreground">
                            {a.titre || a.organisation || "Activité"}
                          </div>
                          {a.titre && a.organisation && (
                            <div className="text-muted-foreground">
                              {a.organisation}
                            </div>
                          )}
                          <div className="mt-0.5 text-xs text-muted-foreground/70">
                            {period(a)}
                          </div>
                          {a.description && (
                            <p className="mt-1 text-muted-foreground">
                              {a.description}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </SectionCard>
              )}
            </div>

            {/* Colonne latérale (sticky) */}
            <div className="space-y-6 lg:sticky lg:top-6 lg:self-start">

              {/* Coordonnées & profil */}
              <SectionCard title="Coordonnées & profil">
                <div className="space-y-3">
                  <InfoRow icon={Mail} label="Email" value={candidate.email} />
                  <InfoRow
                    icon={Phone}
                    label="Téléphone"
                    value={candidate.telephone}
                  />
                  <InfoRow icon={MapPin} label="Ville" value={candidate.ville} />
                  <InfoRow
                    icon={Building2}
                    label="Secteur"
                    value={candidate.secteur}
                  />
                  <InfoRow
                    icon={Briefcase}
                    label="Spécialité"
                    value={candidate.specialite}
                  />
                  <InfoRow
                    icon={Clock}
                    label="Expérience"
                    value={
                      candidate.experience_texte ??
                      (candidate.annees_experience > 0
                        ? candidate.annees_experience < 1
                          ? "< 1 an"
                          : `${Math.round(candidate.annees_experience)} an(s)`
                        : null)
                    }
                  />
                </div>
              </SectionCard>

              {/* Compétences */}
              {candidate.skills.length > 0 && (
                <SectionCard title="Compétences">
                  <div className="flex flex-wrap gap-1.5">
                    {candidate.skills.map((s) =>
                      s.type === "hard" ? (
                        <Badge
                          key={s.id}
                          className="bg-primary/10 text-primary"
                        >
                          {s.name}
                        </Badge>
                      ) : (
                        <Badge key={s.id} variant="secondary">
                          {s.name}
                        </Badge>
                      ),
                    )}
                  </div>
                </SectionCard>
              )}

              {/* Langues */}
              {candidate.langues.length > 0 && (
                <SectionCard title="Langues">
                  <div className="flex flex-wrap gap-1.5">
                    {candidate.langues.map((l) => (
                      <Badge key={l.id} variant="outline">
                        {l.name}
                        {l.level ? ` · ${l.level}` : ""}
                      </Badge>
                    ))}
                  </div>
                </SectionCard>
              )}

              {/* Documents */}
              <SectionCard title="Documents">
                {candidate.documents.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Aucun document.
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {candidate.documents.map((d) => (
                      <li key={d.id} className="flex items-center gap-2">
                        <FileText className="size-4 shrink-0 text-muted-foreground" />
                        <span className="min-w-0 flex-1 truncate text-sm text-foreground">
                          {d.filename}
                        </span>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="shrink-0"
                          onClick={() => download(d.id)}
                        >
                          <Download className="size-3.5" />
                          <span className="sr-only sm:not-sr-only sm:ml-1">
                            Télécharger
                          </span>
                        </Button>
                      </li>
                    ))}
                  </ul>
                )}
              </SectionCard>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
