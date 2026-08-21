"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Panel } from "@/components/ui";

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics"],
    queryFn: () => api.analytics(),
  });

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Conversion across discovery → offer." />
      {isLoading ? <p>Loading…</p> : null}
      {data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Jobs discovered" value={data.jobs_discovered} />
          <Metric label="Shortlisted" value={data.jobs_shortlisted} />
          <Metric label="Submitted" value={data.applications_submitted} />
          <Metric label="Interviews" value={data.interviews} />
          <Metric label="OA received" value={data.oa_received} />
          <Metric label="Offers" value={data.offers} />
          <Metric label="App → OA" value={`${data.application_to_oa_rate}%`} />
          <Metric label="App → Interview" value={`${data.application_to_interview_rate}%`} />
          <Metric label="App → Offer" value={`${data.application_to_offer_rate}%`} />
          <Metric label="Rejections" value={data.rejections} />
        </div>
      ) : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Panel>
      <p className="text-sm text-ink-700">{label}</p>
      <p className="mt-2 font-display text-3xl">{value}</p>
    </Panel>
  );
}
