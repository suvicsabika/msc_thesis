const hour = 60 * 60 * 1000;
const day = 24 * hour;

function getSlaTiming(ticket) {
  if (ticket.status === "Resolved" || typeof ticket.sla !== "string") {
    return null;
  }

  const match = ticket.sla
    .trim()
    .match(/^(\d+(?:\.\d+)?)\s*(m|min|mins|minutes?|h|hrs?|hours?|d|days?)$/i);
  if (!match || typeof ticket.createdAt !== "string") return null;

  const unit = match[2][0].toLowerCase();
  const duration = Number(match[1]) * { m: 60_000, h: hour, d: day }[unit];
  // SQLite timestamps without an offset represent UTC.
  const date = ticket.createdAt.trim();
  const created = Date.parse(
    /(?:Z|[+-]\d{2}:?\d{2})$/i.test(date) ? date : `${date}Z`,
  );
  const deadline = created + duration;
  if (duration <= 0 || !Number.isFinite(deadline)) return null;

  return { created, duration, deadline };
}

export function getSlaBucket(ticket, now) {
  const timing = getSlaTiming(ticket);
  if (!timing || !Number.isFinite(now) || timing.created > now) return null;
  if (now >= timing.deadline) return "atRisk";
  if (now >= timing.created + timing.duration * 0.8) return "dueSoon";
  return "onTrack";
}

export function buildSlaSummary(tickets, now) {
  const countdown = { atRisk: 0, dueSoon: 0, onTrack: 0 };
  const dailyCounts = Array(7).fill(0);
  const currentStart = now - 7 * day;
  const previousStart = now - 14 * day;
  let current = 0;
  let previous = 0;

  for (const ticket of tickets) {
    const bucket = getSlaBucket(ticket, now);
    if (!bucket) continue;
    countdown[bucket] += 1;
    if (bucket !== "atRisk") continue;

    const { deadline } = getSlaTiming(ticket);
    if (deadline >= currentStart) {
      current += 1;
      const index = Math.min(6, Math.floor((deadline - currentStart) / day));
      dailyCounts[index] += 1;
    } else if (deadline >= previousStart) {
      previous += 1;
    }
  }

  const changePercent =
    previous === 0
      ? null
      : Math.round(((current - previous) / previous) * 1000) / 10;
  const min = Math.min(...dailyCounts);
  const range = Math.max(Math.max(...dailyCounts) - min, 1);

  return {
    countdown,
    riskTrend: {
      changePercent,
      label:
        previous === 0
          ? "No previous 7-day baseline"
          : "Overdue open tickets: last 7 days vs previous 7 days",
      sparkline: dailyCounts
        .map(
          (count, index) =>
            `${3 + (index * 92) / 6},${30 - ((count - min) / range) * 24}`,
        )
        .join(" "),
    },
  };
}
