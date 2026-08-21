const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type TokenResponse = { access_token: string; token_type: string };

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const auth = authHeaders();
  Object.entries(auth).forEach(([k, v]) => headers.set(k, v as string));

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  register: (body: { email: string; password: string; full_name?: string }) =>
    request<TokenResponse>("/api/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) =>
    request<TokenResponse>("/api/auth/login", { method: "POST", body: JSON.stringify(body) }),
  me: () => request<{ id: string; email: string; full_name?: string }>("/api/auth/me"),
  uploadResume: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Resume>("/api/resume/upload", { method: "POST", body: form });
  },
  listResumes: () => request<Resume[]>("/api/resume"),
  getProfile: () => request<CandidateProfile | null>("/api/resume/profile"),
  listJobs: (params?: Record<string, string | number | boolean | undefined>) => {
    const q = new URLSearchParams();
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== "") q.set(k, String(v));
    });
    const qs = q.toString();
    return request<Job[]>(`/api/jobs${qs ? `?${qs}` : ""}`);
  },
  getJob: (id: string) => request<Job>(`/api/jobs/${id}`),
  discoverJobs: (body?: object) =>
    request<Record<string, number | string[]>>("/api/jobs/discover", {
      method: "POST",
      body: JSON.stringify(body || { india_and_remote: true, limit: 80 }),
    }),
  shortlist: (id: string) => request(`/api/jobs/${id}/shortlist`, { method: "POST" }),
  ignore: (id: string) => request(`/api/jobs/${id}/ignore`, { method: "POST" }),
  match: (id: string) => request(`/api/jobs/${id}/match`, { method: "POST" }),
  prepareApplication: (jobId: string) =>
    request<Application>(`/api/applications/prepare?job_id=${jobId}`, { method: "POST" }),
  listApplications: () => request<Application[]>("/api/applications"),
  updateApplication: (id: string, body: object) =>
    request<Application>(`/api/applications/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  submitApplication: (id: string) =>
    request<Application>(`/api/applications/${id}/submit`, { method: "POST" }),
  analytics: () => request<Analytics>("/api/analytics"),
  dashboard: () => request<DashboardSummary>("/api/dashboard"),
};

export type Resume = {
  id: string;
  original_filename: string;
  parse_status: string;
  structured_json: Record<string, unknown>;
  is_primary: boolean;
  created_at: string;
};

export type CandidateProfile = {
  id: string;
  full_name?: string;
  email?: string;
  phone?: string;
  location?: string;
  summary?: string;
  skills: { name: string; category?: string; status: string }[];
  experiences: {
    company?: string;
    title?: string;
    responsibilities: string[];
    technologies: string[];
    status: string;
  }[];
};

export type Job = {
  id: string;
  company: string;
  title: string;
  location?: string;
  remote_type?: string;
  match_score?: number;
  match_classification?: string;
  matched_skills: string[];
  missing_skills: string[];
  match_reasoning?: string;
  requirements: string[];
  salary?: Record<string, unknown> | null;
  posted_at?: string;
  application_url?: string;
  source: string;
  description?: string;
  is_india: boolean;
};

export type Application = {
  id: string;
  job_id: string;
  status: string;
  cover_letter?: string;
  notes?: string;
  applied_at?: string;
  follow_up_at?: string;
  user_confirmed: boolean;
  created_at: string;
};

export type Analytics = {
  jobs_discovered: number;
  jobs_shortlisted: number;
  applications_submitted: number;
  oa_received: number;
  interviews: number;
  offers: number;
  rejections: number;
  application_to_oa_rate: number;
  application_to_interview_rate: number;
  application_to_offer_rate: number;
};

export type DashboardSummary = {
  excellent_matches: number;
  strong_matches: number;
  applications: number;
  applied: number;
  conversion_rate: number;
  upcoming_followups: { id: string; due_at: string; note?: string }[];
  top_matches: { job_id: string; score: number; classification: string; reasoning?: string }[];
};
