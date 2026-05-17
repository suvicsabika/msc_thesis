import { cn } from "../../utils/cn";

export function PriorityBadge({ value }) {
const styles = {
    "Very High": "border-rose-300 bg-rose-100 text-rose-800 shadow-rose-100",
    High: "border-rose-200 bg-rose-50 text-rose-700 shadow-rose-100",
    Medium: "border-amber-200 bg-amber-50 text-amber-700 shadow-amber-100",
    Low: "border-emerald-200 bg-emerald-50 text-emerald-700 shadow-emerald-100",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-black shadow-sm",
        styles[value] ?? "border-slate-200 bg-slate-50 text-slate-700"
      )}
    >
      {value}
    </span>
  );
}