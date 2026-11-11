import { cn } from "../../utils/cn";
import { getSlaBucket } from "../../utils/sla";

export function SlaTimer({ ticket, now }) {
  const styles = {
    atRisk: "text-rose-600 before:border-rose-500 after:bg-rose-500",
    dueSoon: "text-amber-600 before:border-amber-500 after:bg-amber-500",
    onTrack: "text-emerald-600 before:border-emerald-500 after:bg-emerald-500",
  };

  return (
    <span
      className={cn(
        "relative inline-flex items-center gap-2 text-sm font-black before:h-3 before:w-3 before:animate-spin before:rounded-full before:border-2 before:border-t-transparent before:content-[''] after:absolute after:-left-0.5 after:top-1/2 after:h-4 after:w-4 after:-translate-y-1/2 after:animate-ping after:rounded-full after:opacity-20 after:content-['']",
        styles[getSlaBucket(ticket, now)] ??
          "text-slate-600 before:border-slate-400 after:bg-slate-400",
      )}
    >
      {ticket.sla}
    </span>
  );
}
