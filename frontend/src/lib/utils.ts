import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function matchBadge(classification?: string | null) {
  switch (classification) {
    case "excellent":
      return { label: "Excellent Match", emoji: "🔥", className: "bg-ember-500/15 text-ember-500" };
    case "strong":
      return { label: "Strong Match", emoji: "🟢", className: "bg-pine-500/15 text-pine-500" };
    case "possible":
      return { label: "Possible", emoji: "🟡", className: "bg-amber-500/15 text-amber-700" };
    case "weak":
      return { label: "Weak", emoji: "⚪", className: "bg-slate-400/20 text-slate-600" };
    case "skip":
      return { label: "Skip", emoji: "🔴", className: "bg-red-500/15 text-red-600" };
    default:
      return { label: "Unscored", emoji: "·", className: "bg-sand-200 text-ink-700" };
  }
}
