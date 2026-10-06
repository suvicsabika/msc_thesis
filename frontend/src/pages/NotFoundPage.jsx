import { ArrowLeft, Bot } from "lucide-react";
import { Link } from "react-router-dom";
import { usePageTitle } from "../hooks/usePageTitle";

export default function NotFoundPage() {
  usePageTitle("404 - Page not found");

  return (
    <main className="grid min-h-screen place-items-center overflow-hidden bg-[radial-gradient(circle_at_top_left,#dbeafe_0,transparent_30%),radial-gradient(circle_at_top_right,#f5d0fe_0,transparent_28%),linear-gradient(135deg,#f8fafc_0%,#eef2ff_44%,#fff7ed_100%)] px-4 py-8 text-slate-900 sm:px-6">
      <section className="w-full max-w-lg rounded-[2.5rem] border border-white/70 bg-white/75 p-8 text-center shadow-2xl shadow-indigo-100/70 ring-1 ring-white/60 backdrop-blur-2xl sm:p-12">
        <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-500/30">
          <Bot className="h-8 w-8" aria-hidden="true" />
        </div>

        <p className="mt-6 bg-gradient-to-r from-blue-600 via-violet-600 to-fuchsia-500 bg-clip-text text-7xl font-black tracking-tight text-transparent sm:text-8xl">
          404
        </p>
        <h1 className="mt-4 text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">
          Page not found
        </h1>
        <p className="mt-3 text-base font-semibold leading-7 text-slate-500">
          The page you are looking for does not exist.
        </p>

        <Link
          to="/dashboard"
          className="mt-8 inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 px-5 py-3 text-sm font-black text-white shadow-lg shadow-indigo-500/25 transition duration-300 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-indigo-500/30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to dashboard
        </Link>
      </section>
    </main>
  );
}
