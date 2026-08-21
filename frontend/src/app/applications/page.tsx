"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Panel } from "@/components/ui";

const COLUMNS = [
  "DISCOVERED",
  "SHORTLISTED",
  "PREPARING",
  "READY",
  "APPLIED",
  "OA",
  "INTERVIEW",
  "OFFER",
  "REJECTED",
];

export default function ApplicationsPage() {
  const { data: apps = [], isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: () => api.listApplications(),
  });

  return (
    <div>
      <PageHeader
        title="Applications"
        subtitle="Kanban tracker across the full application lifecycle."
      />
      {isLoading ? <p>Loading…</p> : null}
      <div className="flex gap-3 overflow-x-auto pb-4">
        {COLUMNS.map((status) => {
          const items = apps.filter((a) => a.status === status);
          return (
            <Panel key={status} className="min-w-[220px] flex-shrink-0">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-700">
                {status.replaceAll("_", " ")}
              </h2>
              <p className="mt-1 font-display text-2xl">{items.length}</p>
              <ul className="mt-3 space-y-2">
                {items.map((app) => (
                  <li key={app.id}>
                    <Link
                      href={`/applications/${app.id}`}
                      className="block rounded-md bg-white/60 px-2 py-2 text-sm hover:bg-white"
                    >
                      {app.job_id.slice(0, 8)}…
                      <span className="block text-xs text-ink-700">{app.status}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
