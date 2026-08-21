"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Panel } from "@/components/ui";

export default function SettingsPage() {
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api.me() });

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Free-first defaults: Ollama LLM, PostgreSQL + pgvector, Redis, Playwright."
      />
      <Panel>
        <h2 className="font-display text-xl">Account</h2>
        <p className="mt-3 text-sm">Email: {me?.email}</p>
        <p className="text-sm">Name: {me?.full_name || "—"}</p>
      </Panel>
      <Panel className="mt-4">
        <h2 className="font-display text-xl">Providers</h2>
        <ul className="mt-3 space-y-2 text-sm text-ink-700">
          <li>LLM: Ollama (default) · optional Gemini / OpenAI-compatible</li>
          <li>Jobs: Greenhouse + Lever public APIs</li>
          <li>Browser assist: Playwright (no CAPTCHA/MFA bypass)</li>
        </ul>
      </Panel>
    </div>
  );
}
