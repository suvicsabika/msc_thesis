import { cn } from "../../utils/cn";

export function SentimentBadge({ value }) {
  const styles = {
    Negative: "bg-rose-50 text-rose-700 ring-rose-100 before:bg-rose-500",
    Neutral: "bg-slate-50 text-slate-700 ring-slate-200 before:bg-slate-400",
    Positive: "bg-emerald-50 text-emerald-700 ring-emerald-100 before:bg-emerald-500",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-bold ring-1 before:h-1.5 before:w-1.5 before:rounded-full before:content-['']",
        styles[value] ?? "bg-violet-50 text-violet-700 ring-violet-100 before:bg-violet-500"
      )}
    >
      {value}
    </span>
  );
}