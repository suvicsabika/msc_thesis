import { useTickets } from "../hooks/useTickets";
import { TicketPanel } from "../components/tickets/TicketPanel";
import { useDashboardSummary } from "../hooks/useDashboardSummary";

import React, { useMemo, useState } from "react";
import { AlertTriangle, Bot, Inbox, Search, Star, Zap } from "lucide-react";

const fallbackDashboardSummary = {
  kpis: {
    openTickets: 0,
    highPriorityTickets: 0,
    slaAtRiskTickets: 0,
    negativeSentimentTickets: 0,
    resolvedToday: 0,
  },
  priorityDistribution: {
    veryHigh: 0,
    high: 0,
    medium: 0,
    low: 0,
  },
  sentimentBreakdown: {
    negative: 0,
    neutral: 0,
    positive: 0,
    unknown: 0,
  },
  slaCountdown: {
    atRisk: 0,
    dueSoon: 0,
    onTrack: 0,
  },
  workflowActivity: [],
  trends: {
  openTickets: {
    changePercent: null,
    label: "No previous 7-day baseline",
    direction: "none",
    sparkline: "3,26 20,26 32,26 47,26 62,26 78,26 95,26",
  },
  highPriorityTickets: {
    changePercent: null,
    label: "No previous 7-day baseline",
    direction: "none",
    sparkline: "3,26 20,26 32,26 47,26 62,26 78,26 95,26",
  },
  slaAtRiskTickets: {
    changePercent: null,
    label: "No previous 7-day baseline",
    direction: "none",
    sparkline: "3,26 20,26 32,26 47,26 62,26 78,26 95,26",
  },
  negativeSentimentTickets: {
    changePercent: null,
    label: "No previous 7-day baseline",
    direction: "none",
    sparkline: "3,26 20,26 32,26 47,26 62,26 78,26 95,26",
  },
}
};

function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}

const toneMap = {
  blue: {
    card: "from-blue-500/20 via-cyan-400/10 to-transparent",
    icon: "from-blue-600 to-cyan-500 shadow-blue-500/30",
    text: "text-blue-600",
    ring: "ring-blue-200/70",
  },
  rose: {
    card: "from-rose-500/20 via-pink-400/10 to-transparent",
    icon: "from-rose-600 to-pink-500 shadow-rose-500/30",
    text: "text-rose-600",
    ring: "ring-rose-200/70",
  },
  amber: {
    card: "from-amber-500/25 via-orange-400/10 to-transparent",
    icon: "from-amber-500 to-orange-500 shadow-amber-500/30",
    text: "text-amber-600",
    ring: "ring-amber-200/70",
  },
  violet: {
    card: "from-violet-500/20 via-fuchsia-400/10 to-transparent",
    icon: "from-violet-600 to-fuchsia-500 shadow-violet-500/30",
    text: "text-violet-600",
    ring: "ring-violet-200/70",
  },
  emerald: {
    card: "from-emerald-500/20 via-teal-400/10 to-transparent",
    icon: "from-emerald-600 to-teal-500 shadow-emerald-500/30",
    text: "text-emerald-600",
    ring: "ring-emerald-200/70",
  },
  sky: {
    card: "from-sky-500/20 via-blue-400/10 to-transparent",
    icon: "from-sky-500 to-blue-600 shadow-sky-500/30",
    text: "text-sky-600",
    ring: "ring-sky-200/70",
  },
};

function SidebarItem({ icon: Icon, label, active }) {
  return (
    <button
      className={cn(
        "group flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left text-sm font-black transition-all duration-300",
        active
          ? "bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 text-white shadow-xl shadow-indigo-500/25"
          : "text-slate-600 hover:-translate-y-0.5 hover:bg-white/80 hover:text-slate-950 hover:shadow-lg hover:shadow-slate-200/70"
      )}
    >
      <Icon className="h-5 w-5 transition-transform duration-300 group-hover:rotate-3 group-hover:scale-110" />
      {label}
    </button>
  );
}

function KpiCard({ item, index }) {
  const Icon = item.icon;
  const tone = toneMap[item.tone];

  return (
    <article
      className="group relative overflow-hidden rounded-[2rem] border border-white/70 bg-white/80 p-5 shadow-xl shadow-slate-200/70 ring-1 ring-white/60 backdrop-blur-2xl transition-all duration-500 hover:-translate-y-2 hover:scale-[1.015] hover:shadow-2xl hover:shadow-indigo-200/70"
      style={{ animationDelay: `${index * 90}ms` }}
    >
      <div className={cn("absolute -right-10 -top-12 h-36 w-36 rounded-full bg-gradient-to-br blur-2xl transition-transform duration-700 group-hover:scale-125", tone.card)} />
      <div className="absolute inset-0 translate-x-[-120%] bg-gradient-to-r from-transparent via-white/50 to-transparent opacity-0 transition duration-1000 group-hover:translate-x-[120%] group-hover:opacity-100" />

      <div className="relative flex items-start justify-between gap-4">
        <div className={cn("grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br text-white shadow-lg transition-transform duration-500 group-hover:rotate-6 group-hover:scale-110", tone.icon)}>
          <Icon className="h-5 w-5" />
        </div>

        <svg viewBox="0 0 100 36" className="h-10 w-24 opacity-90">
          <polyline
            points={item.sparkline}
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={cn("animate-draw-line", tone.text)}
          />
        </svg>
      </div>

      <div className="relative mt-5">
        <p className="text-sm font-bold text-slate-500">{item.title}</p>
        <p className="mt-2 text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">{item.value}</p>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className={cn("rounded-full bg-white/80 px-2.5 py-1 text-xs font-black ring-1", tone.text, tone.ring)}>{item.change}</span>
          <span className="text-xs font-bold text-slate-400">{item.helper}</span>
        </div>
      </div>
    </article>
  );
}

function Panel({ title, subtitle, children, action, className }) {
  return (
    <section className={cn("group relative overflow-hidden rounded-[2rem] border border-white/70 bg-white/80 p-5 shadow-xl shadow-slate-200/70 ring-1 ring-white/60 backdrop-blur-2xl transition-all duration-500 hover:shadow-2xl hover:shadow-indigo-100", className)}>
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-300/70 to-transparent" />
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-black text-slate-950">{title}</h2>
          {subtitle && <p className="mt-1 text-sm font-semibold text-slate-400">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
function getPercent(value, total) {
  return `${Math.round((value / total) * 100)}%`;
}

function DonutChart({ stats }) {
  const total = stats.veryHigh + stats.high + stats.medium + stats.low;
  const safeTotal = total === 0 ? 1 : total;

  const veryHigh = (stats.veryHigh / safeTotal) * 100;
  const high = (stats.high / safeTotal) * 100;
  const medium = (stats.medium / safeTotal) * 100;

  return (
    <div className="flex flex-col items-center gap-6">
      <div
        className="relative grid h-36 w-36 shrink-0 animate-float place-items-center rounded-full shadow-inner shadow-slate-300/80"
        style={{
          background: `conic-gradient(
            #be123c 0 ${veryHigh}%,
            #f43f5e ${veryHigh}% ${veryHigh + high}%,
            #f59e0b ${veryHigh + high}% ${veryHigh + high + medium}%,
            #22c55e ${veryHigh + high + medium}% 100%
          )`,
        }}
      >
        <div className="relative grid h-24 w-24 place-items-center rounded-full bg-white shadow-xl">
          <div className="text-center">
            <p className="text-2xl font-black text-slate-950">
              {total.toLocaleString()}
            </p>
            <p className="text-xs font-bold text-slate-400">Total</p>
          </div>
        </div>
      </div>

      <div className="w-full min-w-0 flex-1 space-y-3">
        <LegendRow
          color="bg-rose-800"
          label="Very High"
          value={stats.veryHigh}
          percent={getPercent(stats.veryHigh, safeTotal)}
        />

        <LegendRow
          color="bg-rose-500"
          label="High"
          value={stats.high}
          percent={getPercent(stats.high, safeTotal)}
        />

        <LegendRow
          color="bg-amber-500"
          label="Medium"
          value={stats.medium}
          percent={getPercent(stats.medium, safeTotal)}
        />

        <LegendRow
          color="bg-emerald-500"
          label="Low"
          value={stats.low}
          percent={getPercent(stats.low, safeTotal)}
        />
      </div>
    </div>
  );
}

function SentimentBreakdown({ stats }) {
  const total =
    stats.negative + stats.neutral + stats.positive + stats.unknown;

  const safeTotal = total === 0 ? 1 : total;

  return (
    <>
      <div className="mb-5 flex h-4 overflow-hidden rounded-full bg-slate-100 ring-1 ring-slate-200">
        <div
          className="bg-rose-500 transition-all duration-700"
          style={{ width: `${(stats.negative / safeTotal) * 100}%` }}
        />
        <div
          className="bg-amber-500 transition-all duration-700"
          style={{ width: `${(stats.neutral / safeTotal) * 100}%` }}
        />
        <div
          className="bg-emerald-500 transition-all duration-700"
          style={{ width: `${(stats.positive / safeTotal) * 100}%` }}
        />
        <div
          className="bg-violet-500 transition-all duration-700"
          style={{ width: `${(stats.unknown / safeTotal) * 100}%` }}
        />
      </div>

      <div className="space-y-3">
        <LegendRow
          color="bg-rose-500"
          label="Negative"
          value={stats.negative}
          percent={getPercent(stats.negative, safeTotal)}
        />
        <LegendRow
          color="bg-amber-500"
          label="Neutral"
          value={stats.neutral}
          percent={getPercent(stats.neutral, safeTotal)}
        />
        <LegendRow
          color="bg-emerald-500"
          label="Positive"
          value={stats.positive}
          percent={getPercent(stats.positive, safeTotal)}
        />
        <LegendRow
          color="bg-violet-500"
          label="Unknown"
          value={stats.unknown}
          percent={getPercent(stats.unknown, safeTotal)}
        />
      </div>
    </>
  );
}

function LegendRow({ color, label, value, percent }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50/70 px-3 py-2 text-sm transition hover:-translate-y-0.5 hover:bg-white hover:shadow-md">
      <div className="flex items-center gap-2">
        <span className={cn("h-2.5 w-2.5 rounded-full shadow-sm", color)} />
        <span className="font-black text-slate-700">{label}</span>
        <span className="font-semibold text-slate-400">({value})</span>
      </div>
      <span className="font-black text-slate-500">{percent}</span>
    </div>
  );
}

function SlaBox({ value, label, tone, pulse }) {
  const styles = {
    rose: "border-rose-100 bg-rose-50 text-rose-600 shadow-rose-100/70",
    amber: "border-amber-100 bg-amber-50 text-amber-600 shadow-amber-100/70",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-600 shadow-emerald-100/70",
  };

  return (
    <div className={cn("relative rounded-3xl border p-4 text-center shadow-lg transition duration-300 hover:-translate-y-1 hover:scale-[1.03]", styles[tone])}>
      {pulse && (
        <span className="absolute right-3 top-3 flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
        </span>
      )}
      <p className="text-3xl font-black">{value}</p>
      <p className="mt-1 text-xs font-black uppercase tracking-wide">{label}</p>
    </div>
  );
}

function formatTrendChange(metric) {
  if (metric.changePercent === null || metric.changePercent === undefined) {
    return "New";
  }

  const sign = metric.changePercent > 0 ? "+" : "";

  return `${sign}${metric.changePercent}%`;
}

export default function McpTicketDashboard() {
  const [query, setQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState("All");

  const { tickets, isLoading, error, refetch } = useTickets();

  const {
    summary,
    isLoading: isSummaryLoading,
    error: summaryError,
    refetch: refetchSummary,
  } = useDashboardSummary();

  const dashboardSummary = summary ?? fallbackDashboardSummary;

  const priorityStats = {
  veryHigh: 0,
  high: 0,
  medium: 0,
  low: 0,
  ...(dashboardSummary.priorityDistribution ?? {}),
};
  const sentimentStats = dashboardSummary.sentimentBreakdown;
  const slaCountdown = dashboardSummary.slaCountdown;
  const workflowActivity = dashboardSummary.workflowActivity;

  const filteredTickets = useMemo(() => {
    return tickets.filter((ticket) => {
      const searchableText = [
        ticket.id,
        ticket.subject,
        ticket.customer,
        ticket.category,
        ticket.priority,
        ticket.sentiment,
        ticket.status,
        ticket.owner,
      ]
        .join(" ")
        .toLowerCase();

      const matchesSearch = searchableText.includes(query.toLowerCase());
      const matchesFilter =
        activeFilter === "All" || ticket.priority === activeFilter;

      return matchesSearch && matchesFilter;
    });
  }, [tickets, query, activeFilter]);

  const kpis = useMemo(() => {
  const trends = dashboardSummary.trends ?? fallbackDashboardSummary.trends;

  return [
    {
      title: "Open Tickets",
      value: dashboardSummary.kpis.openTickets.toLocaleString(),
      change: formatTrendChange(trends.openTickets),
      helper: trends.openTickets.label,
      icon: Inbox,
      tone: "blue",
      sparkline: trends.openTickets.sparkline,
    },
    {
      title: "Very High Priority",
      value: dashboardSummary.priorityDistribution.veryHigh.toLocaleString(),
      change: formatTrendChange(trends.highPriorityTickets),
      helper: trends.highPriorityTickets.label,
      icon: Star,
      tone: "rose",
      sparkline: trends.highPriorityTickets.sparkline,
    },
    {
      title: "SLA Risk Overview",
      value: dashboardSummary.kpis.slaAtRiskTickets.toLocaleString(),
      change: formatTrendChange(trends.slaAtRiskTickets),
      helper: trends.slaAtRiskTickets.label,
      icon: AlertTriangle,
      tone: "amber",
      sparkline: trends.slaAtRiskTickets.sparkline,
    },
    {
      title: "Negative Sentiment",
      value: dashboardSummary.kpis.negativeSentimentTickets.toLocaleString(),
      change: formatTrendChange(trends.negativeSentimentTickets),
      helper: trends.negativeSentimentTickets.label,
      icon: Zap,
      tone: "violet",
      sparkline: trends.negativeSentimentTickets.sparkline,
    },
  ];
}, [dashboardSummary]);

  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-[radial-gradient(circle_at_top_left,#dbeafe_0,transparent_30%),radial-gradient(circle_at_top_right,#f5d0fe_0,transparent_28%),linear-gradient(135deg,#f8fafc_0%,#eef2ff_44%,#fff7ed_100%)] text-slate-900">
      <style>{`
        @keyframes float { 0%, 100% { transform: translateY(0px) rotate(0deg); } 50% { transform: translateY(-16px) rotate(2deg); } }
        @keyframes floatReverse { 0%, 100% { transform: translateY(0px) rotate(0deg); } 50% { transform: translateY(14px) rotate(-2deg); } }
        @keyframes drawLine { from { stroke-dashoffset: 160; } to { stroke-dashoffset: 0; } }
        @keyframes gridMove { from { background-position: 0 0; } to { background-position: 48px 48px; } }
        .animate-float { animation: float 6s ease-in-out infinite; }
        .animate-float-reverse { animation: floatReverse 7s ease-in-out infinite; }
        .animate-draw-line { stroke-dasharray: 160; animation: drawLine 1.8s ease-out both; }
        .animated-grid { background-image: linear-gradient(rgba(99,102,241,.08) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,.08) 1px, transparent 1px); background-size: 48px 48px; animation: gridMove 18s linear infinite; }
      `}</style>

      <div className="pointer-events-none fixed inset-0 animated-grid opacity-60" />
      <div className="pointer-events-none fixed -left-24 top-56 h-80 w-80 animate-float rounded-full bg-violet-400/25 blur-3xl" />
      <div className="pointer-events-none fixed -right-28 bottom-8 h-96 w-96 animate-float-reverse rounded-full bg-cyan-300/25 blur-3xl" />
      <div className="pointer-events-none fixed left-1/2 top-16 h-72 w-72 -translate-x-1/2 animate-pulse rounded-full bg-fuchsia-300/10 blur-3xl" />

      <header className="sticky top-0 z-50 border-b border-white/70 bg-white/70 backdrop-blur-2xl">
        <div className="mx-auto flex h-20 w-full max-w-[1920px] items-center gap-4 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3 lg:min-w-72">
            <div className="relative grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-500/30">
              <Bot className="h-6 w-6" />
              <span className="absolute -right-1 -top-1 h-3 w-3 animate-ping rounded-full bg-emerald-400" />
              <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-emerald-400 ring-2 ring-white" />
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-lg font-black tracking-tight text-slate-950 sm:text-xl">MCP Ticket Analyzer</h1>
              <p className="hidden text-xs font-bold text-slate-400 sm:block">Ticket processing engineer console</p>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2 sm:gap-3">


  <button className="hidden items-center gap-3 rounded-2xl border border-slate-200 bg-white px-3 py-2 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg lg:flex">
    <div className="relative grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br from-slate-900 to-indigo-700 text-sm font-black text-white">
      CS
      <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-emerald-400 ring-2 ring-white" />
    </div>

    <div className="text-left">
      <p className="text-sm font-black text-slate-900">Csaba Süvöltős</p>
      <p className="text-xs font-bold text-slate-400">Solution Support Engineer</p>
    </div>

  </button>

</div>
        </div>
      </header>

      <div className="relative grid min-w-0 grid-cols-1 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <aside className="hidden min-h-[calc(100vh-5rem)] space-y-5 overflow-y-auto border-r border-white/70 bg-white/45 p-6 backdrop-blur-2xl lg:block">                      <Panel title="Priority Distribution" subtitle="Live visual triage split">
                <DonutChart stats={priorityStats} />
              </Panel>

              <Panel title="Sentiment Breakdown" subtitle="Customer mood overview">
  <SentimentBreakdown stats={sentimentStats} />
</Panel>
        </aside>

        <main className="relative min-w-0 p-4 sm:p-6 lg:p-8">
          <section className="mx-auto mb-6 max-w-[1600px] overflow-hidden rounded-[2.3rem] border border-white/70 bg-white/65 p-5 shadow-xl shadow-indigo-100/70 ring-1 ring-white/70 backdrop-blur-2xl sm:p-7">
            <div className="relative flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
              <div className="absolute -right-20 -top-24 h-56 w-56 animate-float rounded-full bg-gradient-to-br from-indigo-400/20 to-fuchsia-400/10 blur-3xl" />
              <div className="relative">
                <div className="inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white/70 px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-indigo-600 shadow-sm">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" />
                  Ticket processing engineer view
                </div>
                <h2 className="mt-4 max-w-4xl text-4xl font-black tracking-tight text-slate-950 sm:text-5xl xl:text-6xl">
                  Ticket Overview
                  <span className="bg-gradient-to-r from-blue-600 via-violet-600 to-fuchsia-500 bg-clip-text text-transparent"> Dashboard</span>
                </h2>
                <p className="mt-4 max-w-3xl text-base font-semibold leading-7 text-slate-500 sm:text-lg">
                  Responsive customer support interface with a visual dashboard view, SLA risk indicators, priority overview, and MCP tool workflow visualization.
                </p>
                
              </div>
              
              <Panel title="SLA Countdown" subtitle="Risk-sensitive workload">
                <div className="grid grid-cols-3 gap-3">
                  <SlaBox value={slaCountdown.atRisk} label="At Risk" tone="rose" />
                  <SlaBox value={slaCountdown.dueSoon} label="Due Soon" tone="amber" />
                  <SlaBox value={slaCountdown.onTrack} label="On Track" tone="emerald" pulse />
                </div>
              </Panel>
            </div>
          </section>

          <div className="mb-5 block md:hidden">
            <div className="relative">
              <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="h-12 w-full rounded-2xl border border-slate-200 bg-white/90 pl-12 pr-4 text-sm font-bold text-slate-700 outline-none shadow-lg shadow-slate-200/60"
                placeholder="Search tickets..."
              />
            </div>
          </div>

          <div className="mx-auto grid max-w-[1600px] grid-cols-1 gap-5 sm:grid-cols-2 2xl:grid-cols-4">
            {kpis.map((item, index) => (
              <KpiCard key={item.title} item={item} index={index} />
            ))}
          </div>

          <div className="mx-auto mt-5 grid max-w-[1600px] min-w-0 grid-cols-1 gap-5 2xl:grid-cols-[minmax(0,1fr)_24rem]">
            <div className="min-w-0 space-y-5">
                        <TicketPanel
            tickets={filteredTickets}
            query={query}
            onQueryChange={setQuery}
            activeFilter={activeFilter}
            onFilterChange={setActiveFilter}
            isLoading={isLoading}
            error={error}
            onRetry={refetch}
          />
            </div>

            <aside className="min-w-0 space-y-5">



              <Panel title="Recent Workflow Activity" subtitle="Latest engineer-facing events">
                <div className="space-y-4">
                  {workflowActivity.map((item) => (
                    <div key={`${item.ticket}-${item.text}`} className="group flex items-start gap-3 rounded-2xl p-2 transition hover:bg-slate-50">
                      <span className={cn("mt-2 h-2.5 w-2.5 rounded-full ring-4 ring-slate-100 transition group-hover:scale-125", item.color)} />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-bold text-slate-600">
                          <span className="font-black text-blue-600">{item.ticket}</span> {item.text}
                        </p>
                      </div>
                      <span className="text-xs font-black text-slate-400">{item.time}</span>
                    </div>
                  ))}
                </div>
              </Panel>
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
}
