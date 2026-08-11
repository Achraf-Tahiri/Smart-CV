"use client";

import { useState, type FormEvent } from "react";
import { Loader2 } from "lucide-react";

import type { CandidateInput } from "@/lib/api";
import { SECTEURS, SENIORITES, STATUSES } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const NONE_SENTINEL = "__none__";

const STATUS_LABELS: Record<string, string> = {
  pending: "En attente",
  processing: "En traitement",
  success: "Traité",
  manual_review: "À vérifier",
  failed: "Échoué",
};

interface Props {
  initial?: Partial<CandidateInput>;
  onSubmit: (data: CandidateInput) => void;
  submitLabel: string;
  busy?: boolean;
}

export function CandidateForm({ initial, onSubmit, submitLabel, busy }: Props) {
  const [form, setForm] = useState<CandidateInput>({
    prenom: initial?.prenom ?? "",
    nom: initial?.nom ?? "",
    email: initial?.email ?? "",
    telephone: initial?.telephone ?? "",
    ville: initial?.ville ?? "",
    poste_actuel: initial?.poste_actuel ?? "",
    secteur: initial?.secteur ?? "",
    specialite: initial?.specialite ?? "",
    annees_experience: initial?.annees_experience ?? 0,
    seniorite: initial?.seniorite ?? "",
    status: initial?.status ?? "success",
  });

  function set<K extends keyof CandidateInput>(key: K, value: CandidateInput[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit(form);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Section Identité */}
      <div className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Identité
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="prenom">Prénom</Label>
            <Input
              id="prenom"
              value={form.prenom ?? ""}
              onChange={(e) => set("prenom", e.target.value)}
              placeholder="Prénom"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="nom">Nom</Label>
            <Input
              id="nom"
              value={form.nom ?? ""}
              onChange={(e) => set("nom", e.target.value)}
              placeholder="Nom de famille"
            />
          </div>
        </div>
      </div>

      <div className="border-t" />

      {/* Section Coordonnées */}
      <div className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Coordonnées
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={form.email ?? ""}
              onChange={(e) => set("email", e.target.value)}
              placeholder="email@example.com"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="telephone">Téléphone</Label>
            <Input
              id="telephone"
              value={form.telephone ?? ""}
              onChange={(e) => set("telephone", e.target.value)}
              placeholder="+212 6 00 00 00 00"
            />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="ville">Ville</Label>
            <Input
              id="ville"
              value={form.ville ?? ""}
              onChange={(e) => set("ville", e.target.value)}
              placeholder="Casablanca"
            />
          </div>
        </div>
      </div>

      <div className="border-t" />

      {/* Section Profil */}
      <div className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Profil
        </p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="poste_actuel">Poste actuel</Label>
            <Input
              id="poste_actuel"
              value={form.poste_actuel ?? ""}
              onChange={(e) => set("poste_actuel", e.target.value)}
              placeholder="Développeur Full-Stack"
            />
          </div>

          <div className="space-y-1.5">
            <Label>Secteur</Label>
            <Select
              value={form.secteur || NONE_SENTINEL}
              onValueChange={(v) => set("secteur", v === NONE_SENTINEL ? "" : v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="— Non renseigné" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE_SENTINEL}>— Non renseigné</SelectItem>
                {SECTEURS.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="specialite">Spécialité</Label>
            <Input
              id="specialite"
              value={form.specialite ?? ""}
              onChange={(e) => set("specialite", e.target.value)}
              placeholder="React, Node.js…"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="annees_experience">Années d&apos;expérience</Label>
            <Input
              id="annees_experience"
              type="number"
              min={0}
              step={0.5}
              value={form.annees_experience ?? 0}
              onChange={(e) => set("annees_experience", Number(e.target.value))}
            />
          </div>

          <div className="space-y-1.5">
            <Label>Séniorité</Label>
            <Select
              value={form.seniorite || NONE_SENTINEL}
              onValueChange={(v) => set("seniorite", v === NONE_SENTINEL ? "" : v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="— Non renseigné" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE_SENTINEL}>— Non renseigné</SelectItem>
                {SENIORITES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5 sm:col-span-2">
            <Label>Statut</Label>
            <Select
              value={form.status ?? "success"}
              onValueChange={(v) => set("status", v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {STATUS_LABELS[s] ?? s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="border-t" />

      <Button type="submit" disabled={busy} className="w-full sm:w-auto">
        {busy && <Loader2 className="size-4 animate-spin" />}
        {busy ? "Enregistrement…" : submitLabel}
      </Button>
    </form>
  );
}
