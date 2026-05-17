import { cn } from "../../utils/cn";

export function StatusBadge({ value }) {
  const styles = {
    Open: "bg-blue-50 text-blue-700 ring-blue-200",
    Resolved: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    "In Progress": "bg-indigo-50 text-indigo-700 ring-indigo-200",
  };

  return (
    <span
      className={cn(
        "rounded-full px-2.5 py-1 text-xs font-black ring-1",
        styles[value] ?? "bg-slate-50 text-slate-700 ring-slate-200"
      )}
    >
      {value}
    </span>
  );
}