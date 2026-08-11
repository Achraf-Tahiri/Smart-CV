import { cn } from "@/lib/utils";

/** Icône de marque Smart CV (logo carré). */
export function BrandIcon({ className }: { className?: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/smart-cv-icon.svg"
      alt="Smart CV"
      width={32}
      height={32}
      className={cn("size-8 rounded-[10px] object-contain", className)}
    />
  );
}

/** Bloc logo + nom (compact), utilisé dans la sidebar et l'en-tête mobile.
 *  La baseline « Un projet par Achraf Tahiri » (≈261 px) ne tient pas
 *  dans la sidebar (w-64) ni le tiroir mobile → activable via `tagline` seulement
 *  dans les contextes larges (ex. panneau du login). */
export function BrandWordmark({
  className,
  tagline = false,
}: {
  className?: string;
  tagline?: boolean;
}) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <BrandIcon />
      <div className="flex flex-col leading-none">
        <span className="whitespace-nowrap font-display text-[15px] font-semibold tracking-tight text-foreground">
          Smart <span className="text-primary">CV</span>
        </span>
        {tagline && (
          <span className="mt-1 whitespace-nowrap text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
            Un projet par Achraf Tahiri
          </span>
        )}
      </div>
    </div>
  );
}
