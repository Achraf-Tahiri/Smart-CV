"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MenuIcon, PlusIcon } from "lucide-react";

import { useAuth } from "@/app/providers";
import { BrandWordmark } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { canWrite } from "@/lib/roles";
import { SidebarNav } from "./sidebar-nav";
import { UserMenu } from "./user-menu";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const router = useRouter();
  const { user } = useAuth();
  const showNew = !!user && canWrite(user.role);

  return (
    <div className="min-h-svh bg-background lg:grid lg:grid-cols-[minmax(16rem,20%)_minmax(0,1fr)]">
      {/* Sidebar (bureau) */}
      <aside className="hidden min-w-0 border-r border-sidebar-border bg-sidebar lg:block">
        <div className="sticky top-0 flex h-dvh flex-col">
          <div className="flex h-16 shrink-0 items-center border-b border-sidebar-border px-5">
            <Link
              href="/dashboard"
              aria-label="Aller au tableau de bord"
              className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <BrandWordmark />
            </Link>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-3 py-4">
            <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
              Espace de travail
            </p>
            <SidebarNav />
          </div>
          <div className="shrink-0 border-t border-sidebar-border p-3">
            <UserMenu />
          </div>
        </div>
      </aside>

      {/* Colonne principale */}
      <div className="flex min-h-svh min-w-0 flex-col">
        <header className="sticky top-0 z-20 flex h-16 shrink-0 items-center gap-3 border-b border-border bg-background/85 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/70 md:px-6">
          {/* Menu mobile */}
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="lg:hidden"
                aria-label="Ouvrir le menu"
              >
                <MenuIcon />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="h-dvh w-72 max-w-full gap-0 p-0">
              <SheetHeader className="h-16 shrink-0 justify-center border-b border-sidebar-border px-5">
                <SheetTitle className="p-0">
                  <Link
                    href="/dashboard"
                    aria-label="Aller au tableau de bord"
                    onClick={() => setMobileOpen(false)}
                  >
                    <BrandWordmark />
                  </Link>
                </SheetTitle>
              </SheetHeader>
              <div className="min-h-0 flex-1 overflow-y-auto p-3">
                <SidebarNav onNavigate={() => setMobileOpen(false)} />
              </div>
              <div className="shrink-0 border-t border-sidebar-border p-3">
                <UserMenu />
              </div>
            </SheetContent>
          </Sheet>

          <Link
            href="/dashboard"
            aria-label="Aller au tableau de bord"
            className="lg:hidden"
          >
            <BrandWordmark />
          </Link>

          <div className="ml-auto flex items-center gap-1.5">
            {showNew && (
              <Button
                className="hidden sm:inline-flex"
                onClick={() => router.push("/candidates/new")}
              >
                <PlusIcon />
                Nouveau candidat
              </Button>
            )}
            <ThemeToggle />
          </div>
        </header>

        <main className="flex-1">
          {process.env.NEXT_PUBLIC_PREVIEW_MODE === "true" && (
            <div role="note" className="border-b border-indigo-200 bg-indigo-50 px-6 py-2.5 text-center text-xs font-medium text-indigo-800 dark:border-indigo-900 dark:bg-indigo-950 dark:text-indigo-200">
              Démonstration · Données entièrement fictives · Lecture seule
            </div>
          )}
          <div className="w-full px-4 py-6 md:px-6 md:py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
