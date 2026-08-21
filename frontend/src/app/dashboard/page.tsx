"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Panel } from "@/components/ui";

export default function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.dashboard(),
  });

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Upload → Find → Review → Prepare → Apply → Track"
        actions={
          <>
            <Link href="/resume" className="rounded-md bg-pine-500 px-3.5 py-2 text-sm text-white">
              Upload resume
            </Link>
            <Link href="/jobs" className="rounded-md bg-ink-900 px-3.5 py-2 text-sm text-sand-50">
              Find jobs
            </Link>
          </>
        }
      />

      {isLoading ? <p>Loading…</p> : null}
      {error ? <p className="text-red-600">{(error as Error).message}</p> : null}

      {data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Excellent matches" value={data.excellent_matches} />
          <Stat label="Strong matches" value={data.strong_matches} />
          <Stat label="Applications" value={data.applications} />
          <Stat label="Conversion" value={`${data.conversion_rate}%`} />
        </div>
      ) : null}

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Panel>
          <h2 className="font-display text-xl">Top matches</h2>
          <ul className="mt-4 space-y-3">
            {(data?.top_matches || []).map((m) => (
              <li key={m.job_id} className="border-b border-ink-900/10 pb-3 last:border-0">
                <Link href={`/jobs/${m.job_id}`} className="font-medium hover:underline">
                  Score {Math.round(m.score)} · {m.classification}
                </Link>
                <p className="text-sm text-ink-700">{m.reasoning}</p>
              </li>
            ))}
            {!data?.top_matches?.length ? (
              <p className="text-sm text-ink-700">Discover jobs to see ranked matches.</p>
            ) : null}
          </ul>
        </Panel>
        <Panel>
          <h2 className="font-display text-xl">Upcoming follow-ups</h2>
          <ul className="mt-4 space-y-3">
            {(data?.upcoming_followups || []).map((f) => (
              <li key={f.id} className="text-sm">
                <span className="font-medium">{new Date(f.due_at).toLocaleDateString()}</span>
                <span className="text-ink-700"> — {f.note || "Follow up"}</span>
              </li>
            ))}
            {!data?.upcoming_followups?.length ? (
              <p className="text-sm text-ink-700">No follow-ups yet.</p>
            ) : null}
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <Panel>
      <p className="text-sm text-ink-700">{label}</p>
      <p className="mt-2 font-display text-3xl text-ink-950">{value}</p>
    </Panel>
  );
}
