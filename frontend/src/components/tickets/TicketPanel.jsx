import { ArrowRight, MoreVertical, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { cn } from "../../utils/cn";
import { MobileTicketCard } from "./MobileTicketCard";
import { PriorityBadge } from "./PriorityBadge";
import { SentimentBadge } from "./SentimentBadge";
import { StatusBadge } from "./StatusBadge";
import { SlaTimer } from "./SlaTimer";
export function TicketPanel({
  tickets,
  query,
  onQueryChange,
  activeFilter,
  onFilterChange,
  isLoading,
  error,
  onRetry,
}) {
  return (
    <section className="group relative overflow-hidden rounded-[2rem] border border-white/70 bg-white/80 p-5 shadow-xl shadow-slate-200/70 ring-1 ring-white/60 backdrop-blur-2xl transition-all duration-500 hover:shadow-2xl hover:shadow-indigo-100">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-300/70 to-transparent" />

      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-base font-black text-slate-950">Recent Tickets</h2>
          <p className="mt-1 text-sm font-semibold text-slate-400">
            {tickets.length} visible tickets · responsive ticket overview
          </p>
        </div>
      </div>

      <div className="mb-5 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="relative w-full xl:max-w-md">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            className="h-12 w-full rounded-2xl border border-slate-200 bg-white/90 pl-12 pr-4 text-sm font-bold text-slate-700 outline-none shadow-sm transition focus:border-indigo-300 focus:shadow-lg focus:shadow-indigo-100"
            placeholder="Search tickets..."
          />
        </div>

        <div className="grid grid-cols-4 gap-2 sm:flex sm:flex-wrap">
          {["All", "Very High", "High", "Medium", "Low"].map((filter) => (
            <button
              key={filter}
              onClick={() => onFilterChange(filter)}
              className={cn(
                "rounded-2xl px-4 py-3 text-sm font-black shadow-sm transition duration-300 hover:-translate-y-0.5 hover:shadow-lg",
                activeFilter === filter
                  ? "bg-gradient-to-r from-blue-600 to-violet-600 text-white shadow-indigo-500/25"
                  : "border border-slate-200 bg-white text-slate-600"
              )}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {isLoading && (
        <div className="grid gap-3">
          {[1, 2, 3, 4].map((item) => (
            <div
              key={item}
              className="h-16 animate-pulse rounded-2xl bg-slate-100"
            />
          ))}
        </div>
      )}

      {error && !isLoading && (
        <div className="rounded-3xl border border-rose-200 bg-rose-50 p-5 text-rose-700">
          <p className="font-black">Loading failed</p>
          <p className="mt-1 text-sm font-semibold">{error}</p>
          <button
            onClick={onRetry}
            className="mt-4 rounded-2xl bg-rose-600 px-4 py-2 text-sm font-black text-white shadow-lg shadow-rose-500/20 transition hover:-translate-y-0.5 hover:shadow-xl"
          >
            Retry
          </button>
        </div>
      )}

      {!isLoading && !error && tickets.length === 0 && (
        <div className="rounded-3xl border border-slate-200 bg-slate-50 p-8 text-center">
          <p className="text-lg font-black text-slate-800">
            No tickets found
          </p>
          <p className="mt-2 text-sm font-semibold text-slate-500">
            Try changing the search term or selected priority filter.
          </p>
        </div>
      )}

      {!isLoading && !error && tickets.length > 0 && (
        <>
          <div className="space-y-3 md:hidden">
            {tickets.map((ticket) => (
              <MobileTicketCard key={ticket.id} ticket={ticket} />
            ))}
          </div>

          <div className="hidden max-w-full overflow-x-auto md:block">
            <table className="w-full min-w-[1080px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-xs font-black uppercase tracking-wider text-slate-400">
                  <th className="px-3 py-3">Ticket ID</th>
                  <th className="px-3 py-3">Subject</th>
                  <th className="px-3 py-3">Customer</th>
                  <th className="px-3 py-3">Category</th>
                  <th className="px-3 py-3">Priority</th>
                  <th className="px-3 py-3">Sentiment</th>
                  <th className="px-3 py-3">SLA</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3">Owner</th>
                  <th className="px-3 py-3" />
                </tr>
              </thead>

              <tbody>
                {tickets.map((ticket) => (
                  <tr
                    key={ticket.id}
                    className="group border-b border-slate-100 transition duration-300 hover:bg-indigo-50/70"
                  >
                    <td className="whitespace-nowrap px-3 py-4">
                      <Link
                        to={`/tickets/${ticket.id}`}
                        className="font-black text-blue-600 transition hover:text-violet-600 hover:underline"
                      >
                        {ticket.id}
                      </Link>
                    </td>

                    <td className="min-w-72 px-3 py-4 font-black text-slate-800">
                      {ticket.subject}
                    </td>

                    <td className="whitespace-nowrap px-3 py-4 font-semibold text-slate-500">
                      {ticket.customer}
                    </td>

                    <td className="whitespace-nowrap px-3 py-4 font-semibold text-slate-600">
                      {ticket.category}
                    </td>

                    <td className="whitespace-nowrap px-3 py-4">
                      <PriorityBadge value={ticket.priority} />
                    </td>

                    <td className="whitespace-nowrap px-3 py-4">
                      <SentimentBadge value={ticket.sentiment} />
                    </td>

                    <td className="whitespace-nowrap px-3 py-4">
                      <SlaTimer value={ticket.sla} state={ticket.slaState} />
                    </td>

                    <td className="whitespace-nowrap px-3 py-4">
                      <StatusBadge value={ticket.status} />
                    </td>

                    <td className="whitespace-nowrap px-3 py-4">
                      <div className="flex items-center gap-2">
                        <span className="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br from-slate-800 to-indigo-700 text-xs font-black text-white shadow-md">
                          {ticket.owner.slice(0, 1)}
                        </span>
                        <span className="font-bold text-slate-500">
                          {ticket.owner}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}