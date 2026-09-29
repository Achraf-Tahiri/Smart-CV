import { cn } from "@/lib/utils";

/** Smart CV document-and-checkmark mark. */
export function BrandIcon({ className }: { className?: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src="/smart-cv-icon.svg" alt="Smart CV" width={32} height={32}
      className={cn("size-8 rounded-[10px]", className)} />
  );
}

export function BrandWordmark({ className, tagline = true }: {
  className?: string;
  tagline?: boolean;
}) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <BrandIcon />
      <div className="flex flex-col leading-none">
        <span className="whitespace-nowrap font-display text-[17px] font-semibold tracking-tight text-foreground">
          Smart <span className="text-primary">CV</span>
        </span>
        {tagline && <span className="mt-1.5 text-[10px] font-medium tracking-wide text-muted-foreground">by Achraf Tahiri</span>}
      </div>
    </div>
  );
}
