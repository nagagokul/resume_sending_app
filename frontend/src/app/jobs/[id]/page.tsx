"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button, PageHeader, Panel } from "@/components/ui";
import { matchBadge } from "@/lib/utils";

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const { data: job, isLoading } = useQuery({
    queryKey: ["job", params.id],
    queryFn: () => api.getJob(params.id),
  });

  const shortlist = useMutation({
    mutationFn: () => api.shortlist(params.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["job", params.id] }),
  });
  const prepare = useMutation({
    mutationFn: () => api.prepareApplication(params.id),
    onSuccess: (app) => router.push(`/applications/${app.id}`),
  });

  if (isLoading || !job) return <p>Loading…</p>;
  const badge = matchBadge(job.match_classification);

  return (
    <div>
      <PageHeader
        title={job.title}
        subtitle={`${job.company} · ${job.location || "Location TBD"} · ${job.source}`}
        actions={
          <>
            <Button variant="secondary" onClick={() => shortlist.mutate()}>
              Shortlist
            </Button>
            <Button onClick={() => prepare.mutate()}>Prepare Application</Button>
            {job.application_url ? (
              <a href={job.application_url} target="_blank" rel="noreferrer">
                <Button variant="ghost">Open official page</Button>
              </a>
            ) : null}
          </>
        }
      />

      <div className="mb-4 flex items-center gap-3">
        <span className={`rounded-md px-2 py-1 text-sm ${badge.className}`}>
          {badge.emoji} {badge.label}
        </span>
        {job.match_score != null ? (
          <span className="font-display text-2xl">{Math.round(job.match_score)}</span>
        ) : null}
      </div>

      {job.match_reasoning ? (
        <Panel className="mb-4">
          <h2 className="font-display text-lg">Why this match</h2>
          <p className="mt-2 text-ink-700">{job.match_reasoning}</p>
        </Panel>
      ) : null}

      <Panel>
        <h2 className="font-display text-lg">Description</h2>
        <div
          className="prose prose-sm mt-3 max-w-none text-ink-800"
          dangerouslySetInnerHTML={{
            __html: (job.description || "No description").replace(/\n/g, "<br/>"),
          }}
        />
      </Panel>
    </div>
  );
}
