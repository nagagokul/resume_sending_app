"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/jobs", label: "Jobs" },
  { href: "/applications", label: "Applications" },
  { href: "/resume", label: "Resume" },
  { href: "/analytics", label: "Analytics" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    setAuthed(!!token);
    if (!token && pathname !== "/login" && pathname !== "/") {
      router.replace("/login");
    }
  }, [pathname, router]);

  const isPublic = pathname === "/login" || pathname === "/";

  if (authed === null && !isPublic) {
    return (
      <div className="flex min-h-screen items-center justify-center text-ink-700">
        Loading…
      </div>
    );
  }

  if (isPublic) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-ink-900/10 bg-sand-50/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Link href="/dashboard" className="font-display text-xl tracking-tight text-ink-950">
            Pathfind
          </Link>
          <nav className="flex flex-wrap items-center gap-1 text-sm">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-md px-3 py-1.5 transition",
                  pathname.startsWith(item.href)
                    ? "bg-ink-900 text-sand-50"
                    : "text-ink-700 hover:bg-ink-900/5",
                )}
              >
                {item.label}
              </Link>
            ))}
            <button
              type="button"
              className="ml-2 rounded-md px-3 py-1.5 text-ink-700 hover:bg-ink-900/5"
              onClick={() => {
                localStorage.removeItem("token");
                router.push("/login");
              }}
            >
              Sign out
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8 animate-rise">{children}</main>
    </div>
  );
}
