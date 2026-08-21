"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button, PageHeader, Panel } from "@/components/ui";

export default function ResumePage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);

  const { data: resumes = [] } = useQuery({
    queryKey: ["resumes"],
    queryFn: () => api.listResumes(),
  });
  const { data: profile } = useQuery({
    queryKey: ["profile"],
    queryFn: () => api.getProfile(),
  });

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadResume(file),
    onSuccess: () => {
      setMessage("Resume parsed into verified candidate facts.");
      qc.invalidateQueries({ queryKey: ["resumes"] });
      qc.invalidateQueries({ queryKey: ["profile"] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  return (
    <div>
      <PageHeader
        title="Resume"
        subtitle="Upload PDF, DOCX, or TXT. Facts are marked VERIFIED / INFERRED / MISSING — never invented."
        actions={
          <>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) upload.mutate(file);
              }}
            />
            <Button onClick={() => inputRef.current?.click()} disabled={upload.isPending}>
              {upload.isPending ? "Uploading…" : "Upload resume"}
            </Button>
          </>
        }
      />

      {message ? <p className="mb-4 text-sm text-pine-500">{message}</p> : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel>
          <h2 className="font-display text-xl">Uploaded files</h2>
          <ul className="mt-4 space-y-3">
            {resumes.map((r) => (
              <li key={r.id} className="border-b border-ink-900/10 pb-3 text-sm last:border-0">
                <p className="font-medium">{r.original_filename}</p>
                <p className="text-ink-700">
                  {r.parse_status} · {new Date(r.created_at).toLocaleString()}
                  {r.is_primary ? " · primary" : ""}
                </p>
              </li>
            ))}
            {!resumes.length ? <p className="text-sm text-ink-700">No resume uploaded yet.</p> : null}
          </ul>
        </Panel>

        <Panel>
          <h2 className="font-display text-xl">Candidate profile</h2>
          {profile ? (
            <div className="mt-4 space-y-3 text-sm">
              <p>
                <span className="text-ink-700">Name:</span> {profile.full_name || "—"}
              </p>
              <p>
                <span className="text-ink-700">Email:</span> {profile.email || "—"}
              </p>
              <p>
                <span className="text-ink-700">Location:</span> {profile.location || "—"}
              </p>
              {profile.summary ? <p className="text-ink-800">{profile.summary}</p> : null}
              <div>
                <p className="mb-2 text-ink-700">Skills</p>
                <div className="flex flex-wrap gap-1.5">
                  {profile.skills.map((s) => (
                    <span key={s.name} className="rounded bg-pine-500/10 px-2 py-0.5 text-xs text-pine-500">
                      {s.name}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-2 text-ink-700">Experience</p>
                <ul className="space-y-2">
                  {profile.experiences.map((e, i) => (
                    <li key={i}>
                      <p className="font-medium">
                        {e.title} {e.company ? `@ ${e.company}` : ""}
                      </p>
                      <p className="text-ink-700">{(e.responsibilities || []).slice(0, 2).join(" · ")}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-ink-700">Upload a resume to build your knowledge base.</p>
          )}
        </Panel>
      </div>
    </div>
  );
}
