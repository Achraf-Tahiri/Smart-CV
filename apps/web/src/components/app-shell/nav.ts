import {
  LayoutDashboardIcon,
  UploadCloudIcon,
  UsersIcon,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  match: (pathname: string) => boolean;
  /** Réservé aux rôles pouvant importer (recruteur+). */
  requiresUpload?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  {
    label: "Tableau de bord",
    href: "/dashboard",
    icon: LayoutDashboardIcon,
    match: (p) => p === "/dashboard",
  },
  {
    label: "Candidats",
    href: "/candidates",
    icon: UsersIcon,
    match: (p) => p.startsWith("/candidates"),
  },
  {
    label: "Importer",
    href: "/upload",
    icon: UploadCloudIcon,
    match: (p) => p.startsWith("/upload"),
    requiresUpload: true,
  },
];
