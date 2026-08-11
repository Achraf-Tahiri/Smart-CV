"use client";

import Link from "next/link";
import { ArrowUpRight, Briefcase, MapPin, Search } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { useRequireAuth } from "@/app/providers";
import { searchCandidates, type Candidate, type Page } from "@/lib/api";
import { SECTEURS } from "@/lib/constants";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/status-badge";
import { cn } from "@/lib/utils";

const LIMIT = 10;
const ALL_SENTINEL = "__all__";

function candidateName(c: Candidate): string {
  return [c.prenom, c.nom].filter(Boolean).join(" ") || "(Sans nom)";
}

function initials(c: Candidate): string {
  const p = c.prenom?.trim()[0]?.toUpperCase() ?? "";
  const n = c.nom?.trim()[0]?.toUpperCase() ?? "";
  return p + n || "?";
}

function expLabel(c: Candidate): string | null {
  const y = c.annees_experience;
  if (y > 0) {
    if (y < 1) return "< 1 an d'exp.";
    const r = Math.round(y);
    return `${r} an${r > 1 ? "s" : ""} d'exp.`;
  }
  return c.experience_texte ?? null;
}

// ─── Skeleton ────────────────────────────────────────────────────────────────

function CandidateRowSkeleton() {
  return (
    <div className="flex items-start gap-3 rounded-xl border bg-card p-4">
      <Skeleton className="size-11 shrink-0 rounded-lg" />
      <div className="flex flex-1 flex-col gap-2">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-3 w-64" />
        <div className="flex gap-3 pt-1">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-16" />
        </div>
      </div>
      <Skeleton className="h-5 w-24 shrink-0 rounded-full" />
    </div>
  );
}

// ─── Candidate card ───────────────────────────────────────────────────────────

function CandidateRow({ candidate: c }: { candidate: Candidate }) {
  const name = candidateName(c);
  const exp = expLabel(c);
  const subtitle = [c.poste_actuel, c.secteur].filter(Boolean).join(" · ");

  return (
    <Link
      href={`/candidates/${c.id}`}
      className={cn(
        "group relative flex items-start gap-3 rounded-xl border bg-card p-4 text-card-foreground",
        "transition-colors hover:border-primary/50 hover:bg-accent/30",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
      )}
    >
      {/* accent rail on hover */}
      <span
        aria-hidden
        className="absolute inset-y-3 left-0 w-0.5 rounded-full bg-primary/0 transition-colors group-hover:bg-primary"
      />

      <Avatar className="size-11 shrink-0 rounded-lg">
        <AvatarFallback className="rounded-lg bg-primary/10 font-medium text-primary text-sm">
          {initials(c)}
        </AvatarFallback>
      </Avatar>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="truncate font-semibold leading-tight text-foreground">
            {name}
          </span>
          <ArrowUpRight className="size-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
        </div>

        {subtitle && (
          <p className="mt-0.5 truncate text-sm text-muted-foreground">{subtitle}</p>
        )}

        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {c.ville && (
            <span className="inline-flex items-center gap-1">
              <MapPin className="size-3.5" />
              {c.ville}
            </span>
          )}
          {exp && (
            <span className="inline-flex items-center gap-1">
              <Briefcase className="size-3.5" />
              {exp}
            </span>
          )}
          {c.seniorite && (
            <Badge variant="outline" className="font-normal">
              {c.seniorite}
            </Badge>
          )}
        </div>
      </div>

      <StatusBadge status={c.status} className="shrink-0" />
    </Link>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export default function CandidatesPage() {
  const { user } = useRequireAuth();
  const [name, setName] = useState("");
  const [secteur, setSecteur] = useState("");
  const [ville, setVille] = useState("");
  const [minExp, setMinExp] = useState("");
  const [data, setData] = useState<Page<Candidate> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSearch = useCallback(
    async (offset: number) => {
      setLoading(true);
      setError(null);
      try {
        const result = await searchCandidates({
          name: name || undefined,
          secteur: secteur || undefined,
          ville: ville || undefined,
          min_experience: minExp ? Number(minExp) : undefined,
          limit: LIMIT,
          offset,
        });
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur de recherche.");
      } finally {
        setLoading(false);
      }
    },
    [name, secteur, ville, minExp],
  );

  useEffect(() => {
    if (user) runSearch(0);
    // Chargement initial une fois connecté.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    runSearch(0);
  }

  if (!user) return null;

  const offset = data?.offset ?? 0;
  const total = data?.total ?? 0;

  return (
    <div className="space-y-6">
      {/* En-tête */}
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground">Candidats</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Parcourez et filtrez la base de candidats.
        </p>
      </div>

      {/* Filtres */}
      <Card className="p-4">
        <form onSubmit={onSubmit}>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div className="lg:col-span-2">
              <Label htmlFor="filter-name" className="sr-only">
                Nom du candidat
              </Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                <Input
                  id="filter-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Nom du candidat"
                  className="pl-9"
                />
              </div>
            </div>

            <Select
              value={secteur || ALL_SENTINEL}
              onValueChange={(v) => setSecteur(v === ALL_SENTINEL ? "" : v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Secteur" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_SENTINEL}>Tous les secteurs</SelectItem>
                {SECTEURS.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Input
              value={ville}
              onChange={(e) => setVille(e.target.value)}
              placeholder="Ville"
            />

            <Input
              value={minExp}
              onChange={(e) => setMinExp(e.target.value)}
              type="number"
              min={0}
              placeholder="Exp. min (ans)"
            />
          </div>

          <div className="mt-3">
            <Button type="submit" className="w-full sm:w-auto">
              <Search className="size-4" />
              Rechercher
            </Button>
          </div>
        </form>
      </Card>

      {/* Erreur */}
      {error && (
        <p className="rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </p>
      )}

      {/* Squelettes */}
      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <CandidateRowSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Résultats */}
      {data && !loading && (
        <>
          <p className="text-sm text-muted-foreground">
            {total === 0
              ? "Aucun résultat"
              : `${total} candidat${total > 1 ? "s" : ""}`}
          </p>

          {data.items.length > 0 ? (
            <ul className="space-y-3">
              {data.items.map((c) => (
                <li key={c.id}>
                  <CandidateRow candidate={c} />
                </li>
              ))}
            </ul>
          ) : (
            <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed bg-card py-16 text-center">
              <Search className="size-10 text-muted-foreground/40" />
              <p className="font-medium text-foreground">Aucun candidat ne correspond</p>
              <p className="max-w-xs text-sm text-muted-foreground">
                Essayez d&apos;élargir vos critères de recherche.
              </p>
            </div>
          )}

          {/* Pagination */}
          {total > LIMIT && (
            <div className="flex items-center justify-between">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={offset === 0}
                onClick={() => runSearch(Math.max(0, offset - LIMIT))}
              >
                ← Précédent
              </Button>
              <span className="text-xs text-muted-foreground">
                {total === 0 ? 0 : offset + 1}–{Math.min(offset + LIMIT, total)} sur {total}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={offset + LIMIT >= total}
                onClick={() => runSearch(offset + LIMIT)}
              >
                Suivant →
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
