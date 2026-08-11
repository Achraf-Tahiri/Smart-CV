"use client";

import * as React from "react";
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
    <div className="min-h-svh bg-background">
      {/* Sidebar (bureau) */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
        <div className="flex h-16 items-center border-b border-sidebar-border px-5">
          <BrandWordmark />
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-4">
          <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            Espace de travail
          </p>
          <SidebarNav />
        </div>
        <div className="border-t border-sidebar-border p-3">
          <UserMenu />
        </div>
      </aside>

      {/* Colonne principale */}
      <div className="flex min-h-svh flex-col lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-background/85 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/70 md:px-6">
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
            <SheetContent side="left" className="w-72 p-0">
              <SheetHeader className="h-16 justify-center border-b border-sidebar-border px-5">
                <SheetTitle className="p-0">
                  <BrandWordmark />
                </SheetTitle>
              </SheetHeader>
              <div className="flex flex-1 flex-col justify-between overflow-y-auto p-3">
                <SidebarNav onNavigate={() => setMobileOpen(false)} />
                <div className="border-t border-sidebar-border pt-3">
                  <UserMenu />
                </div>
              </div>
            </SheetContent>
          </Sheet>

          <div className="lg:hidden">
            <BrandWordmark />
          </div>

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
          <div className="mx-auto max-w-6xl px-4 py-6 md:px-6 md:py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
