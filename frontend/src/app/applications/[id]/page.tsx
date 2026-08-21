"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Button, PageHeader, Panel } from "@/components/ui";

export default function ApplicationDetailPage() {
  const params = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { data: app, isLoading } = useQuery({
    queryKey: ["application", params.id],
    queryFn: async () => {
      const apps = await api.listApplications();
      return apps.find((a) => a.id === params.id) || null;
    },
  });
  const { data: job } = useQuery({
    queryKey: ["job", app?.job_id],
    queryFn: () => api.getJob(app!.job_id),
    enabled: !!app?.job_id,
  });

  const confirm = useMutation({
    mutationFn: () => api.updateApplication(params.id, { user_confirmed: true, status: "READY" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["application", params.id] }),
  });

  const submit = useMutation({
    mutationFn: () => api.submitApplication(params.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["application", params.id] });
      qc.invalidateQueries({ queryKey: ["applications"] });
    },
  });

  if (isLoading || !app) return <p>Loading…</p>;

  return (
    <div>
      <PageHeader
        title="Review & Apply"
        subtitle="Explicit confirmation required. CAPTCHA/MFA must be completed manually on the official site."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel>
          <h2 className="font-display text-xl">Job</h2>
          <p className="mt-2 font-medium">{job?.title || app.job_id}</p>
          <p className="text-sm text-ink-700">{job?.company}</p>
          {job?.application_url ? (
            <a
              className="mt-3 inline-block text-sm text-pine-500 underline"
              href={job.application_url}
              target="_blank"
              rel="noreferrer"
            >
              Open official application page
            </a>
          ) : null}
        </Panel>
        <Panel>
          <h2 className="font-display text-xl">Status</h2>
          <p className="mt-2 font-display text-2xl">{app.status}</p>
          <p className="mt-2 text-sm text-ink-700">
            Confirmed: {app.user_confirmed ? "Yes" : "No"}
          </p>
          {app.follow_up_at ? (
            <p className="text-sm text-ink-700">
              Follow up: {new Date(app.follow_up_at).toLocaleDateString()}
            </p>
          ) : null}
        </Panel>
      </div>

      <Panel className="mt-4">
        <h2 className="font-display text-xl">Potential risks</h2>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-ink-700">
          <li>Do not invent experience, employers, or credentials.</li>
          <li>Stop and complete CAPTCHA / MFA manually if prompted.</li>
          <li>Review every autofilled field before submitting on the employer site.</li>
        </ul>
      </Panel>

      <div className="mt-6 flex flex-wrap gap-3">
        <Button variant="secondary" onClick={() => confirm.mutate()} disabled={confirm.isPending}>
          Mark reviewed & ready
        </Button>
        <Button onClick={() => submit.mutate()} disabled={!app.user_confirmed || submit.isPending}>
          Confirm applied (manual submit on site)
        </Button>
      </div>
      {submit.error ? (
        <p className="mt-3 text-sm text-red-600">{(submit.error as Error).message}</p>
      ) : null}
    </div>
  );
}
