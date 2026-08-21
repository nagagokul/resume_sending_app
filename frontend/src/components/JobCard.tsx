"use client";

import Link from "next/link";
import { matchBadge } from "@/lib/utils";
import type { Job } from "@/lib/api";
import { Button } from "@/components/ui";

export function JobCard({
  job,
  onShortlist,
  onIgnore,
  onPrepare,
}: {
  job: Job;
  onShortlist?: () => void;
  onIgnore?: () => void;
  onPrepare?: () => void;
}) {
  const badge = matchBadge(job.match_classification);
  return (
    <article className="rounded-xl border border-ink-900/10 bg-sand-50/80 p-5 shadow-soft transition hover:border-pine-500/30">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-ink-700">{job.company}</p>
          <h3 className="font-display text-xl text-ink-950">
            <Link href={`/jobs/${job.id}`} className="hover:underline">
              {job.title}
            </Link>
          </h3>
          <p className="mt-1 text-sm text-ink-700">
            {job.location || "Location TBD"}
            {job.remote_type ? ` · ${job.remote_type}` : ""}
            {job.source ? ` · ${job.source}` : ""}
          </p>
        </div>
        <div className="text-right">
          <span className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ${badge.className}`}>
            {badge.emoji} {badge.label}
          </span>
          {job.match_score != null ? (
            <p className="mt-2 font-display text-2xl text-ink-950">{Math.round(job.match_score)}</p>
          ) : null}
        </div>
      </div>

      {job.match_reasoning ? (
        <p className="mt-3 text-sm text-ink-700">{job.match_reasoning}</p>
      ) : null}

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <SkillList label="Matched" skills={job.matched_skills} tone="good" />
        <SkillList label="Missing" skills={job.missing_skills} tone="warn" />
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        <Link href={`/jobs/${job.id}`}>
          <Button variant="ghost">View</Button>
        </Link>
        {onShortlist ? (
          <Button variant="secondary" onClick={onShortlist}>
            Shortlist
          </Button>
        ) : null}
        {onPrepare ? (
          <Button onClick={onPrepare}>Prepare Application</Button>
        ) : null}
        {job.application_url ? (
          <a href={job.application_url} target="_blank" rel="noreferrer">
            <Button variant="ghost">Open Application</Button>
          </a>
        ) : null}
        {onIgnore ? (
          <Button variant="ghost" onClick={onIgnore}>
            Ignore
          </Button>
        ) : null}
      </div>
    </article>
  );
}

function SkillList({
  label,
  skills,
  tone,
}: {
  label: string;
  skills: string[];
  tone: "good" | "warn";
}) {
  if (!skills?.length) {
    return (
      <div>
        <p className="text-xs uppercase tracking-wide text-ink-700/70">{label}</p>
        <p className="mt-1 text-sm text-ink-700/60">None listed</p>
      </div>
    );
  }
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-ink-700/70">{label}</p>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {skills.slice(0, 8).map((s) => (
          <span
            key={s}
            className={
              tone === "good"
                ? "rounded bg-pine-500/10 px-2 py-0.5 text-xs text-pine-500"
                : "rounded bg-ember-500/10 px-2 py-0.5 text-xs text-ember-500"
            }
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}
