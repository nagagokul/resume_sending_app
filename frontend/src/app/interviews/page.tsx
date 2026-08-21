"use client";

import { PageHeader, Panel } from "@/components/ui";

export default function InterviewsPage() {
  return (
    <div>
      <PageHeader
        title="Interviews"
        subtitle="Preparation plans unlock when an application reaches interview stage (Phase 12)."
      />
      <Panel>
        <p className="text-ink-700">
          Move an application to INTERVIEW or TECHNICAL_INTERVIEW to generate role-specific prep
          topics from your verified candidate knowledge base.
        </p>
      </Panel>
    </div>
  );
}
