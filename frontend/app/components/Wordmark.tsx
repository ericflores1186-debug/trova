import Link from "next/link";

/**
 * Trova wordmark. The dot over the "o" doubles as a map pin -- the only piece
 * of brand furniture, so it stays consistent everywhere.
 */
export function Wordmark({
  size = "md",
  href = "/",
}: {
  size?: "sm" | "md" | "lg";
  href?: string | null;
}) {
  const scale = {
    sm: "text-2xl",
    md: "text-3xl",
    lg: "text-5xl sm:text-6xl",
  }[size];

  const mark = (
    <span className={`font-display ${scale} leading-none tracking-tight text-ink`}>
      Tr
      <span className="relative inline-block">
        o
        <span
          aria-hidden
          className="absolute -top-[0.12em] left-1/2 h-[0.16em] w-[0.16em] -translate-x-1/2 rounded-full bg-clay"
        />
      </span>
      va
    </span>
  );

  if (!href) return mark;

  return (
    <Link href={href} className="inline-block transition-opacity hover:opacity-70">
      {mark}
    </Link>
  );
}
