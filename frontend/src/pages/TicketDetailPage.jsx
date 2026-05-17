import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  Bot,
  Clock3,
  Loader2,
  Mail,
  RefreshCcw,
  Send,
  ShieldCheck,
  Sparkles,
  Tag,
  WandSparkles,
  Zap,
} from "lucide-react";
import {
  analyzeTicket,
  getLatestTicketDraft,
  getTicket,
} from "../apis/ticketsApi";

function badgeClass(value) {
  const styles = {
    High: "bg-rose-50 text-rose-700 ring-rose-200",
    Medium: "bg-amber-50 text-amber-700 ring-amber-200",
    Low: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    Negative: "bg-rose-50 text-rose-700 ring-rose-200",
    Neutral: "bg-slate-50 text-slate-700 ring-slate-200",
    Positive: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    critical: "bg-rose-50 text-rose-700 ring-rose-200",
    warning: "bg-amber-50 text-amber-700 ring-amber-200",
    safe: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    Open: "bg-blue-50 text-blue-700 ring-blue-200",
    "In Progress": "bg-indigo-50 text-indigo-700 ring-indigo-200",
    Resolved: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  };

  return styles[value] ?? "bg-slate-50 text-slate-700 ring-slate-200";
}

function StatusBadge({ value }) {
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-black ring-1 ${badgeClass(value)}`}>
      {value}
    </span>
  );
}

function DetailCard({ title, icon: Icon, children }) {
  return (
    <section className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-white/80 p-5 shadow-xl shadow-slate-200/70 ring-1 ring-white/60 backdrop-blur-2xl">
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-300/70 to-transparent" />
      <div className="mb-5 flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-2xl bg-indigo-50 text-indigo-600">
          <Icon className="h-5 w-5" />
        </div>
        <h2 className="text-base font-black text-slate-950">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function FieldRow({ label, value }) {
  return (
    <div className="rounded-2xl bg-slate-50/80 p-4">
      <p className="text-xs font-black uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="mt-1 break-words text-sm font-bold text-slate-800">
        {value || "Not available"}
      </p>
    </div>
  );
}

export default function TicketDetailPage() {
  const { ticketId } = useParams();

  const [ticket, setTicket] = useState(null);
  const [draft, setDraft] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);

  const loadTicketDetails = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const [ticketResult, draftResult] = await Promise.all([
        getTicket(ticketId),
        getLatestTicketDraft(ticketId),
      ]);

      setTicket(ticketResult);
      setDraft(draftResult);
    } catch (err) {
      console.error("Failed to load ticket details:", err);
      setError("Failed to load ticket details.");
    } finally {
      setIsLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    loadTicketDetails();
  }, [loadTicketDetails]);

  async function handleAnalyzeTicket() {
    try {
      setIsAnalyzing(true);
      setError(null);
      setAnalysisResult(null);

      const result = await analyzeTicket(ticketId);

      setAnalysisResult(result);
      await loadTicketDetails();
    } catch (err) {
      console.error("Failed to analyze ticket:", err);
      setError("Failed to analyze ticket with MCP.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <main className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,#dbeafe_0,transparent_30%),radial-gradient(circle_at_top_right,#f5d0fe_0,transparent_28%),linear-gradient(135deg,#f8fafc_0%,#eef2ff_44%,#fff7ed_100%)] px-4 py-8 text-slate-900 sm:px-6 lg:px-8">
      <div className="pointer-events-none fixed -left-24 top-56 h-80 w-80 animate-pulse rounded-full bg-violet-400/25 blur-3xl" />
      <div className="pointer-events-none fixed -right-28 bottom-8 h-96 w-96 animate-pulse rounded-full bg-cyan-300/25 blur-3xl" />

      <div className="relative mx-auto max-w-7xl">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Link
            to="/"
            className="inline-flex w-fit items-center gap-2 rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 text-sm font-black text-slate-700 shadow-sm backdrop-blur-xl transition hover:-translate-y-0.5 hover:shadow-lg"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to dashboard
          </Link>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={loadTicketDetails}
              className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 text-sm font-black text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg"
            >
              <RefreshCcw className="h-4 w-4" />
              Refresh
            </button>

            <button
              onClick={handleAnalyzeTicket}
              disabled={isAnalyzing || isLoading}
              className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 to-violet-600 px-4 py-3 text-sm font-black text-white shadow-lg shadow-indigo-500/25 transition hover:-translate-y-0.5 hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isAnalyzing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <WandSparkles className="h-4 w-4" />
              )}
              RE-Analyze with MCP
            </button>
            <p className="mt-2 text-sm font-semibold text-slate-500">
                Tickets are analyzed at creation, however you can re-run the analysis after refreshing the ticket data or when new drafts are generated.
            </p>
          </div>
        </div>

        {isLoading && (
          <div className="rounded-[2rem] border border-white/70 bg-white/80 p-8 shadow-xl">
            <div className="space-y-4">
              <div className="h-8 w-64 animate-pulse rounded-2xl bg-slate-100" />
              <div className="h-32 animate-pulse rounded-3xl bg-slate-100" />
              <div className="grid gap-4 md:grid-cols-3">
                <div className="h-24 animate-pulse rounded-3xl bg-slate-100" />
                <div className="h-24 animate-pulse rounded-3xl bg-slate-100" />
                <div className="h-24 animate-pulse rounded-3xl bg-slate-100" />
              </div>
            </div>
          </div>
        )}

        {error && !isLoading && (
          <div className="rounded-3xl border border-rose-200 bg-rose-50 p-5 text-rose-700">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-5 w-5" />
              <div>
                <p className="font-black">Operation failed</p>
                <p className="mt-1 text-sm font-semibold">{error}</p>
              </div>
            </div>
          </div>
        )}

        {ticket && !isLoading && (
          <>
            <section className="mb-6 overflow-hidden rounded-[2.5rem] border border-white/70 bg-white/75 p-6 shadow-2xl shadow-indigo-100/70 ring-1 ring-white/60 backdrop-blur-2xl sm:p-8">
              <div className="relative">
                <div className="absolute -right-16 -top-20 h-52 w-52 rounded-full bg-gradient-to-br from-blue-400/20 to-violet-400/10 blur-3xl" />

                <div className="relative inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white/70 px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-indigo-600 shadow-sm">
                  <Bot className="h-3.5 w-3.5" />
                  Ticket detail
                </div>

                <div className="relative mt-4 flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                  <div>
                    <h1 className="text-4xl font-black tracking-tight text-slate-950 sm:text-5xl">
                      {ticket.id}
                    </h1>
                    <p className="mt-3 max-w-4xl text-lg font-bold text-slate-600">
                      {ticket.subject}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <StatusBadge value={ticket.status} />
                    <StatusBadge value={ticket.priority} />
                    <StatusBadge value={ticket.sentiment} />
                    <StatusBadge value={ticket.slaState} />
                  </div>
                </div>
              </div>
            </section>

            <div className="grid gap-5 xl:grid-cols-[1fr_24rem]">
              <div className="space-y-5">
                <DetailCard title="Customer message" icon={Mail}>
                  <div className="rounded-3xl border border-slate-200 bg-slate-50/80 p-5 text-sm font-semibold leading-7 text-slate-700">
                    {ticket.body}
                  </div>
                </DetailCard>

                <DetailCard title="AI response draft" icon={Sparkles}>
                  {draft ? (
                    <div className="space-y-4">
                      <div className="rounded-3xl border border-slate-200 bg-slate-50/80 p-5 text-sm font-semibold leading-7 text-slate-700 whitespace-pre-wrap">
                        {draft.draft}
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-3 rounded-3xl bg-violet-50 p-4 text-violet-700 ring-1 ring-violet-100">
                        <div>
                          <p className="font-black">
                            Human approval required:{" "}
                            {draft.requiresApproval ? "Yes" : "No"}
                          </p>
                          <p className="mt-1 text-sm font-semibold">
                            {draft.reason}
                          </p>
                        </div>

                        <button
                          type="button"
                          className="inline-flex items-center gap-2 rounded-2xl bg-violet-600 px-4 py-3 text-sm font-black text-white shadow-lg shadow-violet-500/20 transition hover:-translate-y-0.5 hover:shadow-xl"
                        >
                          <Send className="h-4 w-4" />
                          Approve draft
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-3xl border border-slate-200 bg-slate-50 p-8 text-center">
                      <p className="text-lg font-black text-slate-800">
                        No response draft yet
                      </p>
                      <p className="mt-2 text-sm font-semibold text-slate-500">
                        Run MCP analysis to generate a customer response draft.
                      </p>
                    </div>
                  )}
                </DetailCard>

                {analysisResult && (
                  <DetailCard title="Latest MCP tool execution" icon={Zap}>
                    <div className="space-y-3">
                      {analysisResult.mcpToolResults.map((item) => (
                        <div
                          key={item.tool}
                          className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4"
                        >
                          <p className="font-black text-slate-900">
                            {item.tool}
                          </p>
                          <pre className="mt-3 max-h-48 overflow-auto rounded-2xl bg-slate-950 p-4 text-xs font-semibold text-slate-100">
                            {JSON.stringify(item.result, null, 2)}
                          </pre>
                        </div>
                      ))}
                    </div>
                  </DetailCard>
                )}
              </div>

              <aside className="space-y-5">
                <DetailCard title="Ticket metadata" icon={Tag}>
                  <div className="grid gap-3">
                    <FieldRow label="Customer" value={ticket.customer} />
                    <FieldRow label="Customer email" value={ticket.customerEmail} />
                    <FieldRow label="Category" value={ticket.category} />
                    <FieldRow label="Owner" value={ticket.owner} />
                    <FieldRow label="Updated at" value={ticket.updatedAt} />
                  </div>
                </DetailCard>

                <DetailCard title="Triage state" icon={ShieldCheck}>
                  <div className="grid gap-3">
                    <FieldRow label="Priority" value={ticket.priority} />
                    <FieldRow label="Sentiment" value={ticket.sentiment} />
                    <FieldRow label="SLA" value={ticket.sla} />
                    <FieldRow label="SLA state" value={ticket.slaState} />
                    <FieldRow label="Status" value={ticket.status} />
                  </div>
                </DetailCard>

                {/* <DetailCard title="Workflow notes" icon={Clock3}>
                  <div className="space-y-3 text-sm font-semibold leading-6 text-slate-600">
                    <p>
                      This page shows the persisted ticket state after the MCP
                      Host workflow updates the database through MCP tools.
                    </p>
                    <p>
                      The AI model does not directly mutate the database. The
                      Host workflow calls MCP tools to apply validated changes.
                    </p>
                  </div>
                </DetailCard> */}
              </aside>
            </div>
          </>
        )}
      </div>
    </main>
  );
}