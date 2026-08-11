"use client";

import Link from "next/link";
import { useState, useRef, type ChangeEvent, type DragEvent } from "react";
import {
  Upload,
  X,
  FileText,
  Image,
  File,
  Check,
  Loader2,
  AlertCircle,
  ArrowRight,
} from "lucide-react";
import { toast } from "sonner";

import { useRequireAuth } from "@/app/providers";
import {
  getCandidate,
  processDocument,
  uploadDocument,
  type Candidate,
} from "@/lib/api";
import { canUpload } from "@/lib/roles";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { StatusBadge } from "@/components/status-badge";
import { cn } from "@/lib/utils";

const TERMINAL = ["success", "manual_review", "failed"];

const STEPS = ["Import du fichier", "Mise en file", "Analyse IA", "Terminé"] as const;

const RESULT_MESSAGES: Record<string, string> = {
  success: "CV analysé et fiche candidat créée avec succès.",
  manual_review: "Import effectué — la fiche nécessite une vérification manuelle.",
  failed: "L'analyse du CV a échoué. Vous pouvez réessayer.",
};

async function pollUntilDone(candidateId: string): Promise<Candidate> {
  for (let attempt = 0; attempt < 30; attempt++) {
    const candidate = await getCandidate(candidateId);
    if (TERMINAL.includes(candidate.status)) return candidate;
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error("Traitement toujours en cours (délai dépassé). Réessaie plus tard.");
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} Mo`;
}

function FileTypeIcon({ name }: { name: string }) {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (["png", "jpg", "jpeg", "tif", "tiff", "webp"].includes(ext))
    return <Image className="size-5 shrink-0 text-primary" aria-hidden />;
  if (["pdf", "doc", "docx"].includes(ext))
    return <FileText className="size-5 shrink-0 text-primary" aria-hidden />;
  return <File className="size-5 shrink-0 text-primary" aria-hidden />;
}

export default function UploadPage() {
  const { user } = useRequireAuth();
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [step, setStep] = useState(0); // 0=idle, 1=import, 2=queue, 3=analyze, 4=done
  const [result, setResult] = useState<Candidate | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const busy = step > 0 && step < 4;

  function selectFile(f: File) {
    setFile(f);
    setResult(null);
    setStep(0);
  }

  function reset() {
    setFile(null);
    setResult(null);
    setStep(0);
    if (inputRef.current) inputRef.current.value = "";
  }

  function onDragOver(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setIsDragging(true);
  }

  function onDragLeave() {
    setIsDragging(false);
  }

  function onDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) selectFile(dropped);
  }

  function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) selectFile(f);
  }

  async function onSubmit() {
    if (!file || busy) return;
    setResult(null);
    try {
      setStep(1);
      const uploaded = await uploadDocument(file);
      setStep(2);
      await processDocument(uploaded.document_id);
      setStep(3);
      const candidate = await pollUntilDone(uploaded.candidate_id);
      setResult(candidate);
      setStep(4);
      if (candidate.status === "failed") {
        toast.error("L'analyse a échoué.", {
          description: "Vérifiez le fichier ou réessayez.",
        });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Échec de l'import.";
      toast.error(msg);
      setStep(0);
    }
  }

  if (!user) return null;

  if (!canUpload(user.role)) {
    return (
      <div className="max-w-lg">
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            Accès réservé aux recruteurs.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* En-tête */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Importer un CV</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Formats acceptés : PDF, Word (.docx) ou image (PNG, JPG…). Analyse IA automatique.
        </p>
      </div>

      {/* Zone de dépôt — masquée pendant le traitement et après le résultat */}
      {!busy && !result && (
        <Card>
          <CardContent className="space-y-4 p-4">
            <label
              htmlFor="cv-file-input"
              className={cn(
                "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-10 text-center transition-colors",
                isDragging
                  ? "border-primary bg-accent/30"
                  : "border-muted-foreground/20 hover:border-primary/50 hover:bg-accent/10",
              )}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
            >
              <Upload className="size-8 text-muted-foreground" aria-hidden />
              <p className="text-sm">
                <span className="font-medium">Glissez un fichier ici</span>
                <span className="text-muted-foreground"> ou cliquez pour parcourir</span>
              </p>
              <span className="text-xs text-muted-foreground">
                PDF · DOCX · DOC · PNG · JPG · WEBP · TIFF
              </span>
            </label>
            <input
              ref={inputRef}
              id="cv-file-input"
              type="file"
              accept=".pdf,.docx,.doc,.png,.jpg,.jpeg,.tif,.tiff,.webp"
              onChange={onFileChange}
              className="sr-only"
            />

            {file && (
              <div className="flex items-center gap-3 rounded-lg border bg-muted/30 px-4 py-3">
                <FileTypeIcon name={file.name} />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{file.name}</p>
                  <p className="text-xs text-muted-foreground">{formatBytes(file.size)}</p>
                </div>
                <button
                  type="button"
                  onClick={reset}
                  className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
                  aria-label="Retirer le fichier"
                >
                  <X className="size-4" aria-hidden />
                </button>
              </div>
            )}

            <Button onClick={onSubmit} disabled={!file} className="w-full">
              Importer et analyser
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Stepper — visible pendant le traitement */}
      {busy && (
        <Card>
          <CardHeader>
            <CardTitle>Traitement en cours…</CardTitle>
            <CardDescription>Ne fermez pas cet onglet.</CardDescription>
          </CardHeader>
          <CardContent className="pb-6">
            <ol className="space-y-4">
              {STEPS.map((label, i) => {
                const n = i + 1;
                const done = step > n;
                const current = step === n;
                return (
                  <li key={label} className="flex items-center gap-3">
                    <span
                      className={cn(
                        "flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
                        done
                          ? "bg-primary text-primary-foreground"
                          : current
                            ? "border-2 border-primary text-primary"
                            : "border-2 border-muted text-muted-foreground",
                      )}
                    >
                      {done ? (
                        <Check className="size-3.5" aria-hidden />
                      ) : current ? (
                        <Loader2 className="size-3.5 animate-spin" aria-hidden />
                      ) : (
                        n
                      )}
                    </span>
                    <span
                      className={cn(
                        "text-sm",
                        done && "text-muted-foreground line-through",
                        current && "font-medium text-foreground",
                        !done && !current && "text-muted-foreground",
                      )}
                    >
                      {label}
                    </span>
                  </li>
                );
              })}
            </ol>
          </CardContent>
        </Card>
      )}

      {/* Résultat terminal */}
      {result && step === 4 && (
        <Card>
          <CardContent className="space-y-4 p-6">
            <div className="flex items-center gap-2">
              {result.status === "failed" ? (
                <AlertCircle className="size-5 text-destructive" aria-hidden />
              ) : (
                <Check className="size-5 text-primary" aria-hidden />
              )}
              <StatusBadge status={result.status} />
            </div>
            <p className="text-sm text-muted-foreground">
              {RESULT_MESSAGES[result.status] ?? "Traitement terminé."}
            </p>
            <div className="flex flex-wrap gap-3">
              {result.status !== "failed" && (
                <Button asChild>
                  <Link href={`/candidates/${result.id}`}>
                    Voir la fiche candidat
                    <ArrowRight className="size-4" aria-hidden />
                  </Link>
                </Button>
              )}
              <Button variant="outline" onClick={reset}>
                Importer un autre CV
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
