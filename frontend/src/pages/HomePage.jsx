import {
  ArrowRight,
  Bot,
  LayoutDashboard,
  MessageSquarePlus,
  Network,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Link } from "react-router-dom";
import { usePageTitle } from "../hooks/usePageTitle";
import "./HomePage.css";

const benefits = [
  {
    icon: Sparkles,
    title: "Less busywork",
    description: "AI sorts tickets and drafts replies.",
  },
  {
    icon: Network,
    title: "Connected tools",
    description: "Ticket data and actions work together.",
  },
  {
    icon: ShieldCheck,
    title: "Human review",
    description: "Your team reviews every response.",
  },
];

export default function HomePage() {
  usePageTitle("Home");

  return (
    <main className="home-page relative isolate overflow-hidden bg-[radial-gradient(circle_at_top_left,#dbeafe_0,transparent_30%),radial-gradient(circle_at_top_right,#f5d0fe_0,transparent_28%),linear-gradient(135deg,#f8fafc_0%,#eef2ff_44%,#fff7ed_100%)] text-slate-900">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-24 top-1/3 h-72 w-72 rounded-full bg-violet-400/20 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-24 bottom-0 h-80 w-80 rounded-full bg-cyan-300/20 blur-3xl"
      />

      <div className="home-content relative mx-auto w-full max-w-5xl">
        <header className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="home-logo grid shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-500/30">
              <Bot className="h-6 w-6" aria-hidden="true" />
            </div>
            <p className="text-sm font-black tracking-tight text-slate-950 sm:text-lg">
              MCP Ticket Analyzer - Administrator view
            </p>
          </div>
        </header>

        <section className="home-panel rounded-[2.5rem] border border-white/70 bg-white/75 shadow-2xl shadow-indigo-100/70 ring-1 ring-white/60 backdrop-blur-2xl">
          <div className="home-hero text-center">
            <h1 className="home-title font-black tracking-tight text-slate-950">
              Better support.
              <span className="block bg-gradient-to-r from-blue-600 via-violet-600 to-fuchsia-500 bg-clip-text text-transparent">
                Smarter workflows.
              </span>
            </h1>
            <p className="home-intro mx-auto max-w-lg font-semibold text-slate-500">
              Get help with an issue or keep your support team moving.
            </p>
          </div>

          <nav
            aria-label="Get started"
            className="home-actions grid grid-cols-2 gap-3 sm:gap-5"
          >
            <Link
              to="/tickets/new"
              className="home-action group flex flex-col justify-center rounded-2xl bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-500/25 transition duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-indigo-500/30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 sm:rounded-3xl"
            >
              <span className="flex items-center gap-2 text-xs font-semibold text-indigo-100 sm:text-sm">
                <MessageSquarePlus
                  className="h-4 w-4 shrink-0"
                  aria-hidden="true"
                />
                Need support?
              </span>
              <span className="home-action-label flex items-center justify-between gap-2 font-black">
                Create ticket now!
                <ArrowRight
                  className="hidden h-5 w-5 shrink-0 transition-transform group-hover:translate-x-1 sm:block"
                  aria-hidden="true"
                />
              </span>
            </Link>
            <Link
              to="/dashboard"
              className="home-action group flex flex-col justify-center rounded-2xl border border-indigo-100 bg-white/80 text-indigo-700 shadow-lg shadow-slate-200/60 transition duration-300 hover:-translate-y-1 hover:bg-indigo-50 hover:shadow-xl hover:shadow-indigo-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 sm:rounded-3xl"
            >
              <span className="flex items-center gap-2 text-xs font-semibold text-slate-500 sm:text-sm">
                <LayoutDashboard
                  className="h-4 w-4 shrink-0"
                  aria-hidden="true"
                />
                Need data?
              </span>
              <span className="home-action-label flex items-center justify-between gap-2 font-black">
                Continue to dashboard
                <ArrowRight
                  className="hidden h-5 w-5 shrink-0 transition-transform group-hover:translate-x-1 sm:block"
                  aria-hidden="true"
                />
              </span>
            </Link>
          </nav>

          <section className="home-explanation rounded-2xl border border-indigo-100/70 bg-indigo-50/50 text-center">
            <h2 className="text-sm font-black text-slate-950 sm:text-base">
              What is MCP?
            </h2>
            <p className="home-description mx-auto mt-1 max-w-2xl font-semibold text-slate-500">
              Model Context Protocol (MCP) is an open standard that acts as a
              universal connector, allowing artificial intelligence models and
              assistants to securely link with external data sources, files, and
              software tools. Learn more about MCP here:
              <a
                href="https://modelcontextprotocol.io/"
                target="_blank"
                rel="noopener noreferrer"
              >
                https://modelcontextprotocol.io/
              </a>
            </p>
          </section>

          <section
            aria-label="Why it helps"
            className="home-benefits grid grid-cols-3 gap-3 sm:gap-5"
          >
            {benefits.map(({ icon: Icon, title, description }) => (
              <div key={title} className="text-center">
                <Icon
                  className="home-benefit-icon mx-auto text-indigo-500"
                  aria-hidden="true"
                />
                <h2 className="home-benefit-title font-black text-slate-700">
                  {title}
                </h2>
                <p className="home-benefit-description mt-1 font-semibold text-slate-500">
                  {description}
                </p>
              </div>
            ))}
          </section>
        </section>
      </div>
    </main>
  );
}
