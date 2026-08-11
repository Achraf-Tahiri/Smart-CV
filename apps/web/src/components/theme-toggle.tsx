"use client";

import * as React from "react";
import { MoonIcon, SunIcon } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => setMounted(true), []);

  const isDark = resolvedTheme === "dark";

  return (
    <Button
      variant="outline"
      size="icon"
      aria-label="Basculer le thème clair / sombre"
      onClick={() => setTheme(isDark ? "light" : "dark")}
    >
      {/* Rendu neutre avant montage pour éviter tout écart d'hydratation. */}
      {mounted && isDark ? <SunIcon /> : <MoonIcon />}
    </Button>
  );
}
