"use client";

export default function Header() {
  return (
    <header className="border-b border-border-primary bg-surface sticky top-0 z-50">
      <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-mochi-primary">
              <svg
                className="h-6 w-6 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold text-text-primary">
                Weather Insurance
              </h1>
              <p className="text-xs text-text-secondary">GenLayer Protocol</p>
            </div>
          </div>

          <nav className="hidden items-center gap-8 md:flex">
            <a
              href="#"
              className="text-sm text-text-secondary hover:text-mochi-primary transition-colors"
            >
              Docs
            </a>
            <a
              href="#"
              className="text-sm text-text-secondary hover:text-mochi-primary transition-colors"
            >
              API
            </a>
            <a
              href="#"
              className="text-sm text-text-secondary hover:text-mochi-primary transition-colors"
            >
              GitHub
            </a>
          </nav>

          <button className="rounded-lg border border-mochi-primary px-4 py-2 text-sm font-medium text-mochi-primary hover:bg-mochi-primary/10 transition-colors">
            Connect Wallet
          </button>
        </div>
      </div>
    </header>
  );
}