import Link from "next/link";

/**
 * Minimal top nav — solid paper bar, no glass (DESIGN_SPEC anti-slop).
 */
export function SiteHeader() {
  return (
    <header className="border-b border-border bg-background">
      <div className="mx-auto flex h-12 max-w-[1200px] items-center justify-between px-6">
        <Link
          href="/"
          className="text-[14px] font-semibold tracking-tight text-ink"
        >
          Prospectus
        </Link>
        <nav className="flex items-center gap-5 text-[13px] text-ink-muted">
          <Link
            href="/"
            className="transition-colors hover:text-ink"
          >
            Research
          </Link>
          <Link
            href="/eval"
            className="transition-colors hover:text-ink"
          >
            Eval report
          </Link>
          <a
            href="https://github.com/nickcarndt/prospectus"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-ink"
          >
            GitHub
          </a>
        </nav>
      </div>
    </header>
  );
}
