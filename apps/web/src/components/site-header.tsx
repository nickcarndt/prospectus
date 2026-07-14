import Link from "next/link";

/**
 * Minimal top nav — research tool, not a marketing site.
 */
export function SiteHeader() {
  return (
    <header className="border-b border-border bg-background/80 backdrop-blur-[2px]">
      <div className="mx-auto flex h-12 max-w-[1100px] items-center justify-between px-6">
        <Link
          href="/"
          className="text-[14px] font-semibold tracking-tight text-ink"
        >
          Prospectus
        </Link>
        <nav className="flex items-center gap-5 text-[13px] text-ink-muted">
          <Link href="/" className="hover:text-ink">
            Research
          </Link>
          <Link href="/eval" className="hover:text-ink">
            Eval report
          </Link>
        </nav>
      </div>
    </header>
  );
}
