"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { JobCard } from "@/components/JobCard";
import { Button, PageHeader } from "@/components/ui";

export default function JobsPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const [minScore, setMinScore] = useState("");
  const [classification, setClassification] = useState("");

  const { data: jobs = [], isLoading, error } = useQuery({
    queryKey: ["jobs", minScore, classification],
    queryFn: () =>
      api.listJobs({
        min_score: minScore || undefined,
        classification: classification || undefined,
        limit: 50,
      }),
  });

  const discover = useMutation({
    mutationFn: () => api.discoverJobs({ india_and_remote: true, limit: 80, run_matching: true }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const shortlist = useMutation({
    mutationFn: (id: string) => api.shortlist(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["applications"] });
    },
  });

  const ignore = useMutation({
    mutationFn: (id: string) => api.ignore(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const prepare = useMutation({
    mutationFn: (id: string) => api.prepareApplication(id),
    onSuccess: (app) => router.push(`/applications/${app.id}`),
  });

  return (
    <div>
      <PageHeader
        title="Jobs"
        subtitle="India + remote software roles from Greenhouse and Lever public boards."
        actions={
          <Button onClick={() => discover.mutate()} disabled={discover.isPending}>
            {discover.isPending ? "Discovering…" : "Discover jobs"}
          </Button>
        }
      />

      <div className="mb-6 flex flex-wrap gap-3">
        <select
          className="rounded-md border border-ink-900/15 bg-white/70 px-3 py-2 text-sm"
          value={classification}
          onChange={(e) => setClassification(e.target.value)}
        >
          <option value="">All classifications</option>
          <option value="excellent">Excellent</option>
          <option value="strong">Strong</option>
          <option value="possible">Possible</option>
          <option value="weak">Weak</option>
          <option value="skip">Skip</option>
        </select>
        <input
          className="w-32 rounded-md border border-ink-900/15 bg-white/70 px-3 py-2 text-sm"
          placeholder="Min score"
          value={minScore}
          onChange={(e) => setMinScore(e.target.value)}
        />
      </div>

      {discover.data ? (
        <p className="mb-4 text-sm text-pine-500">
          Fetched {String(discover.data.fetched)} · created {String(discover.data.created)} ·
          matched {String(discover.data.matched)}
        </p>
      ) : null}
      {isLoading ? <p>Loading jobs…</p> : null}
      {error ? <p className="text-red-600">{(error as Error).message}</p> : null}

      <div className="space-y-4">
        {jobs.map((job) => (
          <JobCard
            key={job.id}
            job={job}
            onShortlist={() => shortlist.mutate(job.id)}
            onIgnore={() => ignore.mutate(job.id)}
            onPrepare={() => prepare.mutate(job.id)}
          />
        ))}
        {!isLoading && !jobs.length ? (
          <p className="text-ink-700">No jobs yet. Click Discover jobs to ingest public boards.</p>
        ) : null}
      </div>
    </div>
  );
}
