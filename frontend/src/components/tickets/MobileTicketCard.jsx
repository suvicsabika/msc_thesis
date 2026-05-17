import { MoreVertical } from "lucide-react";
import { Link } from "react-router-dom";
import { PriorityBadge } from "./PriorityBadge";
import { SentimentBadge } from "./SentimentBadge";
import { StatusBadge } from "./StatusBadge";
import { SlaTimer } from "./SlaTimer";
export function MobileTicketCard({ ticket }) {
  return (
    <article className="relative overflow-hidden rounded-3xl border border-white/70 bg-white/80 p-4 shadow-lg shadow-slate-200/70 transition duration-300 hover:-translate-y-1 hover:shadow-xl md:hidden">
      <div className="absolute -right-10 -top-12 h-28 w-28 rounded-full bg-gradient-to-br from-blue-400/20 to-violet-400/10 blur-2xl" />

      <div className="relative flex items-start justify-between gap-3">
        <div>
          <Link
            to={`/tickets/${ticket.id}`}
            className="text-sm font-black text-blue-600 transition hover:text-violet-600 hover:underline"
          >
            {ticket.id}
          </Link>
          <h3 className="mt-1 font-black text-slate-900">{ticket.subject}</h3>
          <p className="mt-1 text-sm font-semibold text-slate-500">
            {ticket.customer} · {ticket.category}
          </p>
        </div>

        <button className="rounded-2xl bg-slate-50 p-2 text-slate-400">
          <MoreVertical className="h-4 w-4" />
        </button>
      </div>

      <div className="relative mt-4 flex flex-wrap items-center gap-2">
        <PriorityBadge value={ticket.priority} />
        <SentimentBadge value={ticket.sentiment} />
        <StatusBadge value={ticket.status} />
        <span className="ml-auto">
          <SlaTimer value={ticket.sla} state={ticket.slaState} />
        </span>
      </div>
    </article>
  );
}