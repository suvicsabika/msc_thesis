const relativeTimeFormatter = new Intl.RelativeTimeFormat("en", {
  numeric: "always",
});

const timeUnits = [
  ["year", 365 * 24 * 60 * 60],
  ["month", 30 * 24 * 60 * 60],
  ["week", 7 * 24 * 60 * 60],
  ["day", 24 * 60 * 60],
  ["hour", 60 * 60],
  ["minute", 60],
];

export function formatRelativeTime(createdAt, now = Date.now()) {
  if (typeof createdAt !== "string" || !createdAt.trim()) {
    return "Time unavailable";
  }

  // SQLite can return stored UTC timestamps without a timezone suffix.
  const date = createdAt.trim();
  const timestamp = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(date) ? date : `${date}Z`;
  const createdTime = Date.parse(timestamp);

  if (!Number.isFinite(createdTime)) {
    return "Time unavailable";
  }

  const elapsedSeconds = (now - createdTime) / 1000;

  for (const [unit, seconds] of timeUnits) {
    if (elapsedSeconds >= seconds) {
      return relativeTimeFormatter.format(
        -Math.floor(elapsedSeconds / seconds),
        unit,
      );
    }
  }

  return "Just now";
}
