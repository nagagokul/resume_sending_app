"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { api } from "@/lib/api";
import { Button, Panel } from "@/components/ui";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  full_name: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("register");
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (values) => {
    setError(null);
    try {
      const res =
        mode === "register"
          ? await api.register(values)
          : await api.login({ email: values.email, password: values.password });
      localStorage.setItem("token", res.access_token);
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Auth failed");
    }
  });

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4">
      <p className="mb-2 font-display text-3xl text-ink-950">Pathfind</p>
      <h1 className="mb-6 text-ink-700">
        {mode === "register" ? "Create your workspace" : "Welcome back"}
      </h1>
      <Panel>
        <form className="space-y-4" onSubmit={onSubmit}>
          {mode === "register" ? (
            <label className="block text-sm">
              Full name
              <input
                className="mt-1 w-full rounded-md border border-ink-900/15 bg-white/70 px-3 py-2"
                {...register("full_name")}
              />
            </label>
          ) : null}
          <label className="block text-sm">
            Email
            <input
              type="email"
              className="mt-1 w-full rounded-md border border-ink-900/15 bg-white/70 px-3 py-2"
              {...register("email")}
            />
          </label>
          <label className="block text-sm">
            Password
            <input
              type="password"
              className="mt-1 w-full rounded-md border border-ink-900/15 bg-white/70 px-3 py-2"
              {...register("password")}
            />
          </label>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {mode === "register" ? "Create account" : "Sign in"}
          </Button>
        </form>
        <button
          type="button"
          className="mt-4 text-sm text-ink-700 underline"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Need an account? Register" : "Already registered? Sign in"}
        </button>
      </Panel>
    </div>
  );
}
