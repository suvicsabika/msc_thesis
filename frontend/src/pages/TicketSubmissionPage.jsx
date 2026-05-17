import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Mail,
  Send,
  Sparkles,
  Tag,
  User,
} from "lucide-react";
import { createTicket } from "../apis/ticketsApi";

const initialFormState = {
  customer: "",
  customerEmail: "",
  subject: "",
  category: "General",
  body: "",
};

export default function TicketSubmissionPage() {
  const [formData, setFormData] = useState(initialFormState);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdTicket, setCreatedTicket] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  function updateField(field, value) {
    setFormData((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      setIsSubmitting(true);
      setError(null);
      setCreatedTicket(null);

      const result = await createTicket(formData);

      setCreatedTicket(result);
      setFormData(initialFormState);

      setTimeout(() => {
        navigate("/");
      }, 1200);
    } catch (err) {
      console.error("Failed to submit ticket:", err);
      setError("Failed to submit ticket. Please check the form and try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,#dbeafe_0,transparent_30%),radial-gradient(circle_at_top_right,#f5d0fe_0,transparent_28%),linear-gradient(135deg,#f8fafc_0%,#eef2ff_44%,#fff7ed_100%)] px-4 py-8 text-slate-900 sm:px-6 lg:px-8">
      <div className="pointer-events-none fixed -left-24 top-56 h-80 w-80 animate-pulse rounded-full bg-violet-400/25 blur-3xl" />
      <div className="pointer-events-none fixed -right-28 bottom-8 h-96 w-96 animate-pulse rounded-full bg-cyan-300/25 blur-3xl" />

      <div className="relative mx-auto max-w-5xl">
        <div className="mb-6 flex items-center justify-between gap-4">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 text-sm font-black text-slate-700 shadow-sm backdrop-blur-xl transition hover:-translate-y-0.5 hover:shadow-lg"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to dashboard
          </button>

          <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-black text-emerald-700">
            <span className="h-2 w-2 animate-ping rounded-full bg-emerald-400" />
            API connected
          </span>
        </div>

        <section className="overflow-hidden rounded-[2.5rem] border border-white/70 bg-white/75 p-6 shadow-2xl shadow-indigo-100/70 ring-1 ring-white/60 backdrop-blur-2xl sm:p-8">
          <div className="relative mb-8">
            <div className="absolute -right-16 -top-20 h-52 w-52 rounded-full bg-gradient-to-br from-blue-400/20 to-violet-400/10 blur-3xl" />

            <div className="relative inline-flex items-center gap-2 rounded-full border border-indigo-100 bg-white/70 px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-indigo-600 shadow-sm">
              <Sparkles className="h-3.5 w-3.5" />
              Ticket intake
            </div>

            <h1 className="relative mt-4 text-4xl font-black tracking-tight text-slate-950 sm:text-5xl">
              Submit a new support ticket
            </h1>

            <p className="relative mt-4 max-w-3xl text-base font-semibold leading-7 text-slate-500">
              Create a new customer support ticket that will be stored in the backend database and displayed on the dashboard.
            </p>
          </div>

          {createdTicket && (
            <div className="mb-6 rounded-3xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-700">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="mt-0.5 h-5 w-5" />
                <div>
                  <p className="font-black">Ticket created successfully</p>
                  <p className="mt-1 text-sm font-semibold">
                    New ticket ID: {createdTicket.id}
                  </p>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="mb-6 rounded-3xl border border-rose-200 bg-rose-50 p-5 text-rose-700">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 h-5 w-5" />
                <div>
                  <p className="font-black">Submission failed</p>
                  <p className="mt-1 text-sm font-semibold">{error}</p>
                </div>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="grid gap-5">
            <div className="grid gap-5 md:grid-cols-2">
              <Field label="Customer name" icon={User}>
                <input
                  value={formData.customer}
                  onChange={(event) => updateField("customer", event.target.value)}
                  required
                  className="h-12 w-full rounded-2xl border border-slate-200 bg-white/90 px-4 text-sm font-bold text-slate-700 outline-none transition focus:border-indigo-300 focus:shadow-lg focus:shadow-indigo-100"
                  placeholder="Acme Corp"
                />
              </Field>

              <Field label="Customer email" icon={Mail}>
                <input
                  type="email"
                  value={formData.customerEmail}
                  onChange={(event) => updateField("customerEmail", event.target.value)}
                  required
                  className="h-12 w-full rounded-2xl border border-slate-200 bg-white/90 px-4 text-sm font-bold text-slate-700 outline-none transition focus:border-indigo-300 focus:shadow-lg focus:shadow-indigo-100"
                  placeholder="support@acme.com"
                />
              </Field>
            </div>

            <div className="grid gap-5 md:grid-cols-[1fr_16rem]">
              <Field label="Subject" icon={Tag}>
                <input
                  value={formData.subject}
                  onChange={(event) => updateField("subject", event.target.value)}
                  required
                  className="h-12 w-full rounded-2xl border border-slate-200 bg-white/90 px-4 text-sm font-bold text-slate-700 outline-none transition focus:border-indigo-300 focus:shadow-lg focus:shadow-indigo-100"
                  placeholder="Cannot access the admin dashboard"
                />
              </Field>

              <Field label="Category" icon={Tag}>
                <select
                  value={formData.category}
                  onChange={(event) => updateField("category", event.target.value)}
                  className="h-12 w-full rounded-2xl border border-slate-200 bg-white/90 px-4 text-sm font-bold text-slate-700 outline-none transition focus:border-indigo-300 focus:shadow-lg focus:shadow-indigo-100"
                >
                  <option value="General">General</option>
                  <option value="Access">Access</option>
                  <option value="Billing">Billing</option>
                  <option value="API">API</option>
                  <option value="Bug">Bug</option>
                  <option value="Feature Request">Feature Request</option>
                  <option value="Performance">Performance</option>
                </select>
              </Field>
            </div>

            <Field label="Message" icon={Mail}>
              <textarea
                value={formData.body}
                onChange={(event) => updateField("body", event.target.value)}
                required
                rows={8}
                className="w-full resize-none rounded-3xl border border-slate-200 bg-white/90 p-4 text-sm font-semibold leading-6 text-slate-700 outline-none transition focus:border-indigo-300 focus:shadow-lg focus:shadow-indigo-100"
                placeholder="Describe the customer issue in detail..."
              />
            </Field>

            <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => {
                  setFormData(initialFormState);
                  setError(null);
                  setCreatedTicket(null);
                }}
                className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-black text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg"
              >
                Clear form
              </button>

              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 to-violet-600 px-5 py-3 text-sm font-black text-white shadow-lg shadow-indigo-500/25 transition hover:-translate-y-0.5 hover:shadow-xl hover:shadow-indigo-500/30 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                Submit ticket
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}

function Field({ label, icon: Icon, children }) {
  return (
    <label className="block">
      <span className="mb-2 flex items-center gap-2 text-sm font-black text-slate-700">
        <Icon className="h-4 w-4 text-indigo-500" />
        {label}
      </span>
      {children}
    </label>
  );
}