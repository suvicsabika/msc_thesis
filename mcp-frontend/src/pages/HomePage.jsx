import React from "react";

export default function HomePage() {
  const features = [
    {
      title: "Minimap Extraction",
      text: "A rendszer rögzített UI-régiókból dolgozik, így a vizuális feldolgozás fókuszált, gyors és jól demonstrálható.",
      tag: "Preprocessing",
    },
    {
      title: "Tactical Event Pipeline",
      text: "Dummy MCP toolokkal végigvezethető az analyze_video → stats → summary folyamat, mintha már élne a backend.",
      tag: "Pipeline",
    },
    {
      title: "MCP-First Design",
      text: "A felület nemcsak eredményt mutat, hanem a háttérben keletkező resource-okat és a capability logikát is láthatóvá teszi.",
      tag: "Architecture",
    },
  ];

  const steps = [
    "Videó kiválasztása vagy mintameccs betöltése",
    "Elemzés indítása MCP-kompatibilis pipeline-on",
    "Round statok, heatmap és summary generálása",
    "Toolok, resource-ok és prompt folyamat megtekintése",
  ];

  const sampleMatches = [
    {
      map: "ASCENT",
      mode: "Demo match",
      summary: "A-site fókusz, gyors belépés, magas early activity.",
    },
    {
      map: "BIND",
      mode: "Demo match",
      summary: "Szórtabb mozgás, rotációs mintázatok, közepes kontroll.",
    },
    {
      map: "SUNSET",
      mode: "Demo match",
      summary: "Mid jelenlét, késői döntéshozatal, alacsonyabb tempó.",
    },
  ];

  return (
    <div className="min-h-screen overflow-hidden bg-[#111823] text-white">
      <div className="relative isolate">
        <div className="absolute inset-0 -z-20 bg-[radial-gradient(circle_at_top_left,_rgba(255,70,84,0.22),_transparent_28%),radial-gradient(circle_at_80%_20%,_rgba(186,58,70,0.25),_transparent_25%),linear-gradient(180deg,_#111823_0%,_#0b1018_100%)]" />
        <div className="absolute inset-0 -z-10 opacity-[0.08] [background-image:linear-gradient(rgba(255,255,255,0.4)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.4)_1px,transparent_1px)] [background-size:44px_44px]" />

        <div className="absolute -left-24 top-24 h-72 w-72 rounded-full bg-[#ff4654]/20 blur-3xl animate-pulse" />
        <div className="absolute right-0 top-0 h-80 w-80 translate-x-1/3 -translate-y-1/4 rounded-full bg-[#ba3a46]/25 blur-3xl animate-pulse" />
        <div className="absolute bottom-0 left-1/2 h-80 w-80 -translate-x-1/2 translate-y-1/3 rounded-full bg-[#ff4654]/10 blur-3xl animate-pulse" />

        <header className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-6 lg:px-10">
          <div className="flex items-center gap-3">
            <div className="relative grid h-11 w-11 place-items-center overflow-hidden rounded-none border border-[#ff4654]/50 bg-[#111823] shadow-[0_0_30px_rgba(255,70,84,0.25)]">
              <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,70,84,0.2),transparent_60%)]" />
              <span className="relative text-lg font-black tracking-[0.25em] text-[#ff4654]">
                V
              </span>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.45em] text-white/50">
                Thesis Demo
              </p>
              <h1 className="text-sm font-semibold uppercase tracking-[0.3em] text-white/90">
                Valorant MCP Analyzer
              </h1>
            </div>
          </div>

          <nav className="hidden items-center gap-8 md:flex">
            <a className="text-sm uppercase tracking-[0.25em] text-white/70 transition hover:text-[#ff4654]" href="#features">
              Features
            </a>
            <a className="text-sm uppercase tracking-[0.25em] text-white/70 transition hover:text-[#ff4654]" href="#workflow">
              Workflow
            </a>
            <a className="text-sm uppercase tracking-[0.25em] text-white/70 transition hover:text-[#ff4654]" href="#samples">
              Samples
            </a>
          </nav>
        </header>

        <main className="mx-auto flex w-full max-w-7xl flex-col gap-20 px-6 pb-20 pt-6 lg:px-10 lg:pb-24 lg:pt-10">
          <section className="grid items-center gap-10 lg:grid-cols-[1.15fr_0.85fr] lg:gap-12">
            <div className="relative">
              <div className="mb-6 inline-flex items-center gap-3 border border-white/10 bg-white/5 px-4 py-2 backdrop-blur-md">
                <span className="h-2.5 w-2.5 animate-ping rounded-full bg-[#ff4654]" />
                <span className="text-xs font-medium uppercase tracking-[0.35em] text-white/75">
                  MCP-Compatible Tactical Analysis
                </span>
              </div>

              <h2 className="max-w-4xl text-5xl font-black uppercase leading-[0.95] tracking-tight sm:text-6xl lg:text-7xl">
                Build a
                <span className="mx-3 inline-block text-[#ff4654] drop-shadow-[0_0_18px_rgba(255,70,84,0.55)]">
                  Valorant
                </span>
                analysis front page that actually feels alive.
              </h2>

              <p className="mt-6 max-w-2xl text-base leading-8 text-white/70 sm:text-lg">
                Ez a demóoldal a diplomamunka frontendjének belépőpontja: intenzív
                hero szekcióval, erős kontrasztokkal, mozgó háttérelemekkel és egy
                futurisztikus dashboard-esztétikával készül, kifejezetten a Valorant
                vizuális hangulatára hangolva.
              </p>

              <div className="mt-10 flex flex-col gap-4 sm:flex-row">
                <button className="group relative overflow-hidden border border-[#ff4654] bg-[#ff4654] px-7 py-4 text-sm font-bold uppercase tracking-[0.3em] text-white transition duration-300 hover:scale-[1.02] hover:shadow-[0_0_30px_rgba(255,70,84,0.4)] active:scale-[0.99]">
                  <span className="absolute inset-0 translate-y-full bg-[linear-gradient(180deg,transparent,rgba(255,255,255,0.14))] transition duration-300 group-hover:translate-y-0" />
                  <span className="relative">Start Analysis</span>
                </button>

                <button className="group border border-white/15 bg-white/5 px-7 py-4 text-sm font-bold uppercase tracking-[0.3em] text-white/90 backdrop-blur-md transition duration-300 hover:border-white/30 hover:bg-white/10 hover:text-white">
                  <span className="inline-block transition duration-300 group-hover:-translate-y-0.5">
                    Explore Demo Match
                  </span>
                </button>
              </div>

              <div className="mt-10 grid max-w-2xl gap-4 sm:grid-cols-3">
                {[
                  ["3", "Dummy tools"],
                  ["3", "Core resources"],
                  ["1", "Summary prompt"],
                ].map(([value, label]) => (
                  <div
                    key={label}
                    className="group relative overflow-hidden border border-white/10 bg-white/[0.04] p-5 backdrop-blur-md transition duration-500 hover:-translate-y-1 hover:border-[#ff4654]/40 hover:bg-white/[0.07]"
                  >
                    <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[#ff4654] to-transparent opacity-0 transition duration-500 group-hover:opacity-100" />
                    <div className="text-3xl font-black text-[#ff4654]">{value}</div>
                    <div className="mt-2 text-xs uppercase tracking-[0.3em] text-white/55">
                      {label}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="absolute -inset-6 bg-[radial-gradient(circle,rgba(255,70,84,0.15),transparent_60%)] blur-2xl" />

              <div className="relative overflow-hidden border border-white/10 bg-white/[0.05] p-5 shadow-[0_20px_80px_rgba(0,0,0,0.35)] backdrop-blur-xl">
                <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,70,84,0.12),transparent_45%,transparent_60%,rgba(186,58,70,0.12))]" />
                <div className="absolute right-4 top-4 h-24 w-24 rotate-12 border border-[#ff4654]/20" />
                <div className="absolute bottom-4 left-4 h-16 w-16 -rotate-6 border border-white/10" />

                <div className="relative">
                  <div className="flex items-center justify-between border-b border-white/10 pb-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.35em] text-white/45">
                        Live Preview
                      </p>
                      <h3 className="mt-2 text-2xl font-black uppercase tracking-[0.15em]">
                        Demo Match Card
                      </h3>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full bg-[#ff4654] shadow-[0_0_16px_rgba(255,70,84,0.8)]" />
                      <span className="text-xs uppercase tracking-[0.3em] text-white/55">
                        Active
                      </span>
                    </div>
                  </div>

                  <div className="mt-6 grid gap-4">
                    <div className="grid grid-cols-2 gap-4">
                      <MetricBox label="Map" value="ASCENT" accent />
                      <MetricBox label="Status" value="READY" />
                    </div>

                    <div className="overflow-hidden border border-white/10 bg-[#0d131d] p-4">
                      <div className="mb-4 flex items-center justify-between">
                        <span className="text-xs uppercase tracking-[0.35em] text-white/45">
                          Pipeline Pulse
                        </span>
                        <span className="text-xs uppercase tracking-[0.3em] text-[#ff4654]">
                          synced
                        </span>
                      </div>

                      <div className="space-y-4">
                        {[
                          ["Video ingest", "100%"],
                          ["Event extraction", "84%"],
                          ["Round stats", "72%"],
                          ["Summary layer", "55%"],
                        ].map(([label, width], index) => (
                          <div key={label}>
                            <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.25em] text-white/50">
                              <span>{label}</span>
                              <span>{width}</span>
                            </div>
                            <div className="h-2 overflow-hidden bg-white/5">
                              <div
                                className="h-full bg-gradient-to-r from-[#ba3a46] to-[#ff4654] shadow-[0_0_16px_rgba(255,70,84,0.4)] transition-all duration-1000"
                                style={{ width, animationDelay: `${index * 120}ms` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-3">
                      {[
                        ["Kills", "09"],
                        ["Dominant Zone", "A"],
                        ["Rounds", "12"],
                      ].map(([label, value]) => (
                        <div
                          key={label}
                          className="border border-white/10 bg-white/[0.03] p-4 transition duration-300 hover:border-[#ff4654]/35 hover:bg-white/[0.06]"
                        >
                          <div className="text-xs uppercase tracking-[0.3em] text-white/45">
                            {label}
                          </div>
                          <div className="mt-2 text-2xl font-black text-white">
                            {value}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section id="features" className="grid gap-5 lg:grid-cols-3">
            {features.map((feature, index) => (
              <article
                key={feature.title}
                className="group relative overflow-hidden border border-white/10 bg-white/[0.04] p-6 backdrop-blur-md transition duration-500 hover:-translate-y-2 hover:border-[#ff4654]/45 hover:bg-white/[0.07]"
              >
                <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-transparent via-[#ff4654] to-transparent opacity-0 transition duration-500 group-hover:opacity-100" />
                <div className="mb-4 inline-flex border border-[#ff4654]/30 bg-[#ff4654]/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.35em] text-[#ff8a94]">
                  {feature.tag}
                </div>
                <div className="mb-4 text-5xl font-black text-white/15">0{index + 1}</div>
                <h3 className="text-2xl font-black uppercase leading-tight tracking-[0.06em] text-white">
                  {feature.title}
                </h3>
                <p className="mt-4 leading-7 text-white/68">{feature.text}</p>
              </article>
            ))}
          </section>

          <section id="workflow" className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.35em] text-[#ff4654]">
                Interaction Flow
              </p>
              <h3 className="mt-4 text-4xl font-black uppercase leading-tight sm:text-5xl">
                The homepage should sell the system before the results page even opens.
              </h3>
              <p className="mt-5 max-w-xl text-base leading-8 text-white/70">
                A kezdőoldal célja, hogy már az első pillanatban közvetítse: ez nem egy
                általános admin panel, hanem egy taktikai, elemző és technikai demófelület,
                amely mögött egy MCP-kompatibilis backend-architektúra áll.
              </p>
            </div>

            <div className="grid gap-4">
              {steps.map((step, index) => (
                <div
                  key={step}
                  className="group flex items-start gap-4 border border-white/10 bg-white/[0.04] p-5 transition duration-500 hover:border-[#ff4654]/40 hover:bg-white/[0.07]"
                >
                  <div className="relative mt-0.5 grid h-12 w-12 shrink-0 place-items-center border border-[#ff4654]/30 bg-[#ff4654]/10 text-sm font-black text-[#ff4654] shadow-[0_0_24px_rgba(255,70,84,0.18)]">
                    {String(index + 1).padStart(2, "0")}
                    <div className="absolute inset-0 scale-110 border border-[#ff4654]/10 opacity-0 transition duration-500 group-hover:scale-125 group-hover:opacity-100" />
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.35em] text-white/40">
                      Step {index + 1}
                    </p>
                    <h4 className="mt-2 text-lg font-bold uppercase tracking-[0.08em] text-white">
                      {step}
                    </h4>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section id="samples" className="space-y-6">
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.35em] text-[#ff4654]">
                  Sample Matches
                </p>
                <h3 className="mt-4 text-4xl font-black uppercase sm:text-5xl">
                  Ready-made demo entries
                </h3>
              </div>
              <p className="max-w-xl text-sm leading-7 text-white/62">
                Ezek a kártyák később kattintható mintameccsek lehetnek, amelyek azonnal
                átviszik a felhasználót az elemzési nézetre.
              </p>
            </div>

            <div className="grid gap-5 lg:grid-cols-3">
              {sampleMatches.map((match) => (
                <button
                  key={match.map}
                  className="group relative overflow-hidden border border-white/10 bg-[#0f1620] p-6 text-left transition duration-500 hover:-translate-y-2 hover:border-[#ff4654]/50 hover:shadow-[0_16px_60px_rgba(0,0,0,0.35)]"
                >
                  <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,70,84,0.08),transparent_45%,transparent_65%,rgba(186,58,70,0.08))] opacity-70 transition duration-500 group-hover:opacity-100" />
                  <div className="relative">
                    <div className="flex items-center justify-between">
                      <span className="border border-white/10 bg-white/[0.04] px-3 py-1 text-[10px] font-bold uppercase tracking-[0.35em] text-white/60">
                        {match.mode}
                      </span>
                      <span className="text-xs uppercase tracking-[0.3em] text-[#ff4654]">
                        View
                      </span>
                    </div>
                    <h4 className="mt-8 text-4xl font-black uppercase tracking-[0.15em] text-white">
                      {match.map}
                    </h4>
                    <p className="mt-4 leading-7 text-white/68">{match.summary}</p>
                    <div className="mt-8 flex items-center gap-3 text-xs uppercase tracking-[0.35em] text-white/40">
                      <span className="h-px w-10 bg-[#ff4654]" />
                      Demo dataset ready
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </section>

          <section className="relative overflow-hidden border border-white/10 bg-white/[0.05] px-6 py-8 backdrop-blur-lg sm:px-8 sm:py-10">
            <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,70,84,0.13),transparent_35%,transparent_65%,rgba(186,58,70,0.12))]" />
            <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.35em] text-[#ff4654]">
                  Thesis Frontend Goal
                </p>
                <h3 className="mt-4 max-w-3xl text-3xl font-black uppercase leading-tight sm:text-4xl">
                  Clean enough for a thesis, bold enough to feel like a real product.
                </h3>
              </div>

              <div className="flex flex-col gap-4 sm:flex-row">
                <button className="border border-[#ff4654] bg-[#ff4654] px-6 py-4 text-sm font-bold uppercase tracking-[0.3em] text-white transition duration-300 hover:shadow-[0_0_28px_rgba(255,70,84,0.42)]">
                  Use Sample Match
                </button>
                <button className="border border-white/15 bg-transparent px-6 py-4 text-sm font-bold uppercase tracking-[0.3em] text-white/85 transition duration-300 hover:border-white/35 hover:bg-white/5 hover:text-white">
                  Upload Video
                </button>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

function MetricBox({ label, value, accent = false }) {
  return (
    <div className="relative overflow-hidden border border-white/10 bg-white/[0.04] p-4">
      <div
        className={`absolute inset-x-0 top-0 h-px ${accent ? "bg-gradient-to-r from-transparent via-[#ff4654] to-transparent" : "bg-gradient-to-r from-transparent via-white/30 to-transparent"}`}
      />
      <div className="text-[10px] uppercase tracking-[0.35em] text-white/45">{label}</div>
      <div className={`mt-2 text-3xl font-black uppercase ${accent ? "text-[#ff4654]" : "text-white"}`}>
        {value}
      </div>
    </div>
  );
}
