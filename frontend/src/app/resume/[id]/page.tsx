"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { PageHeader, Panel } from "@/components/ui";

export default function ResumeDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: resumes = [] } = useQuery({
    queryKey: ["resumes"],
    queryFn: () => api.listResumes(),
  });
  const resume = resumes.find((r) => r.id === params.id);

  return (
    <div>
      <PageHeader title={resume?.original_filename || "Resume"} subtitle={resume?.parse_status} />
      <Panel>
        <pre className="overflow-auto text-xs text-ink-800">
          {JSON.stringify(resume?.structured_json || {}, null, 2)}
        </pre>
      </Panel>
    </div>
  );
}
