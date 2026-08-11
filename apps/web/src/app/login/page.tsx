"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import {
  AlertCircleIcon,
  ArrowRightIcon,
  EyeIcon,
  EyeOffIcon,
  Loader2Icon,
  LockIcon,
  MailIcon,
  SparklesIcon,
} from "lucide-react";

import { useAuth } from "@/app/providers";
import { BrandIcon, BrandWordmark } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const STATS = [
  { k: "CV", v: "profils structurés" },
  { k: "OCR", v: "documents numérisés" },
  { k: "API", v: "architecture modulaire" },
];

export default function LoginPage() {
  const { user, login } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) router.replace("/dashboard");
  }, [user, router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de la connexion.");
      setSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-svh lg:grid-cols-[1.05fr_1fr]">
      {/* Panneau de marque */}
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-primary p-10 text-primary-foreground lg:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.13]"
          style={{
            backgroundImage:
              "radial-gradient(circle at 1px 1px, currentColor 1px, transparent 0)",
            backgroundSize: "22px 22px",
          }}
          aria-hidden="true"
        />
        <div className="pointer-events-none absolute -right-24 -top-24 size-80 rounded-full bg-primary-foreground/10 blur-2xl" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 size-96 rounded-full bg-primary-foreground/10 blur-2xl" />

        <div className="relative flex items-center gap-2.5">
          <BrandIcon className="bg-primary-foreground/15" />
          <div className="flex flex-col leading-none">
            <span className="font-display text-lg font-semibold tracking-tight">
              Smart CV
            </span>
            <span className="mt-1 whitespace-nowrap text-[10px] font-medium uppercase tracking-[0.14em] text-primary-foreground/70">
              Un projet par Achraf Tahiri
            </span>
          </div>
        </div>

        <div className="relative flex flex-col gap-6">
          <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-primary-foreground/15 px-3 py-1 text-xs font-medium">
            <SparklesIcon className="size-3.5" />
            Console de recrutement intelligente
          </span>
          <h1 className="max-w-md font-display text-4xl font-semibold leading-[1.1] tracking-tight text-balance">
            Tout votre vivier de talents, structuré et interrogeable.
          </h1>
          <p className="max-w-md text-sm leading-relaxed text-primary-foreground/80">
            Centralisez les CV, lancez des recherches en langage naturel et
            suivez le traitement de chaque candidature — dans une interface
            pensée pour les équipes de recrutement.
          </p>
          <dl className="mt-2 grid max-w-md grid-cols-3 gap-4">
            {STATS.map((s) => (
              <div key={s.v} className="flex flex-col gap-1">
                <dt className="font-display text-2xl font-semibold">{s.k}</dt>
                <dd className="text-xs leading-tight text-primary-foreground/70">
                  {s.v}
                </dd>
              </div>
            ))}
          </dl>
        </div>

        <p className="relative text-xs text-primary-foreground/60">
          Smart CV — un projet par Achraf Tahiri.
        </p>
      </aside>

      {/* Panneau formulaire */}
      <main className="relative flex flex-col items-center justify-center px-5 py-10 sm:px-8">
        <div className="absolute right-4 top-4">
          <ThemeToggle />
        </div>

        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <BrandWordmark />
          </div>

          <div className="mb-7 flex flex-col gap-1.5">
            <h2 className="font-display text-2xl font-semibold tracking-tight">
              Connexion
            </h2>
            <p className="text-sm text-muted-foreground">
              Accédez à votre espace de gestion des candidatures.
            </p>
          </div>

          {error && (
            <div className="mb-5 flex items-start gap-2.5 rounded-lg border border-destructive/30 bg-destructive/10 px-3.5 py-3 text-sm text-destructive">
              <AlertCircleIcon className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={onSubmit} className="flex flex-col gap-5" noValidate>
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Adresse e-mail</Label>
              <div className="relative">
                <MailIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  required
                  autoComplete="username"
                  placeholder="demo@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-11 pl-10"
                />
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Mot de passe</Label>
              <div className="relative">
                <LockIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  required
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-11 pl-10 pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  aria-label={
                    showPassword
                      ? "Masquer le mot de passe"
                      : "Afficher le mot de passe"
                  }
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-sm p-1 text-muted-foreground transition-colors hover:text-foreground"
                >
                  {showPassword ? (
                    <EyeOffIcon className="size-4" />
                  ) : (
                    <EyeIcon className="size-4" />
                  )}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              size="lg"
              className="h-11 w-full"
              disabled={submitting}
            >
              {submitting ? (
                <>
                  <Loader2Icon className="animate-spin" />
                  Connexion…
                </>
              ) : (
                <>
                  Se connecter
                  <ArrowRightIcon />
                </>
              )}
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
}
