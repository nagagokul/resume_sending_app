import Link from "next/link";

export default function HomePage() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-20 top-10 h-72 w-72 rounded-full bg-pine-400/20 blur-3xl animate-pulse-soft" />
        <div className="absolute right-0 top-40 h-80 w-80 rounded-full bg-ember-400/20 blur-3xl animate-pulse-soft" />
      </div>
      <div className="relative mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-6 py-16">
        <p className="font-display text-5xl tracking-tight text-ink-950 sm:text-7xl animate-rise">
          Pathfind
        </p>
        <h1 className="mt-4 max-w-2xl font-display text-2xl text-ink-800 sm:text-3xl animate-rise [animation-delay:80ms]">
          High-quality India & remote engineering matches — not mass spam.
        </h1>
        <p className="mt-4 max-w-xl text-lg text-ink-700 animate-rise [animation-delay:140ms]">
          Upload your resume, discover Greenhouse & Lever roles, rank by real experience,
          and prepare truthful applications with human review.
        </p>
        <div className="mt-8 flex flex-wrap gap-3 animate-rise [animation-delay:200ms]">
          <Link
            href="/login"
            className="rounded-md bg-pine-500 px-5 py-2.5 text-sm font-medium text-white hover:bg-pine-400"
          >
            Get started
          </Link>
          <Link
            href="/dashboard"
            className="rounded-md bg-ink-900 px-5 py-2.5 text-sm font-medium text-sand-50 hover:bg-ink-800"
          >
            Open dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
