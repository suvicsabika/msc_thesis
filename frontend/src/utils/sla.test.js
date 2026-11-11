import assert from "node:assert/strict";
import test from "node:test";
import { buildSlaSummary, getSlaBucket } from "./sla.js";

const hour = 60 * 60 * 1000;
const day = 24 * hour;
const now = Date.parse("2026-11-03T12:00:00Z");

function ticket(created, sla = "1h", status = "Open") {
  return { createdAt: new Date(created).toISOString(), sla, status };
}

test("SLA policy labels use the final 20% and deadline boundaries", () => {
  for (const [sla, duration] of [
    ["1h", hour],
    ["4h", 4 * hour],
    ["12h", 12 * hour],
    ["1 day", day],
    ["1d", day],
    ["30 minutes", hour / 2],
    ["1.5 hours", 1.5 * hour],
  ]) {
    const value = ticket(now, sla);
    assert.equal(getSlaBucket(value, now + duration * 0.8 - 1), "onTrack", sla);
    assert.equal(getSlaBucket(value, now + duration * 0.8), "dueSoon", sla);
    assert.equal(getSlaBucket(value, now + duration - 1), "dueSoon", sla);
    assert.equal(getSlaBucket(value, now + duration), "atRisk", sla);
  }
});

test("SQLite UTC timestamps and explicit timezone offsets agree", () => {
  for (const createdAt of [
    "2026-11-03T11:00:00",
    "2026-11-03T11:00:00Z",
    "2026-11-03T12:00:00+01:00",
    "2026-11-03T06:00:00-0500",
  ]) {
    assert.equal(getSlaBucket({ createdAt, sla: "1h" }, now), "atRisk");
  }
});

test("resolved, future, and invalid tickets do not produce SLA risk", () => {
  for (const value of [
    ticket(now - 2 * hour, "1h", "Resolved"),
    ticket(now + hour),
    ticket(now, "0h"),
    ticket(now, "-1h"),
    ticket(now, "unavailable"),
    ticket(now, null),
    { createdAt: "invalid", sla: "1h" },
    { sla: "1h" },
  ]) {
    assert.equal(getSlaBucket(value, now), null);
  }
});

test("summary counts all unresolved tickets regardless of the trend window", () => {
  const summary = buildSlaSummary(
    [
      ticket(now - 2 * hour),
      ticket(now - 2 * day),
      ticket(now - 8 * day, "1h", "In Progress"),
      ticket(now - 20 * day),
      ticket(now - 50 * 60_000),
      ticket(now - 30 * 60_000),
      ticket(now - 2 * hour, "1h", "Resolved"),
      ticket(now, "unknown"),
    ],
    now,
  );
  assert.deepEqual(summary.countdown, { atRisk: 4, dueSoon: 1, onTrack: 1 });
  assert.equal(summary.riskTrend.changePercent, 100);
  assert.equal(summary.riskTrend.sparkline.split(" ").length, 7);
});

test("risk trends group deadlines into non-overlapping seven-day windows", () => {
  const summary = buildSlaSummary(
    [
      ticket(now - hour),
      ticket(now - 7 * day - hour),
      ticket(now - 14 * day - hour),
      ticket(now - 14 * day - hour - 1),
    ],
    now,
  );
  assert.equal(summary.countdown.atRisk, 4);
  assert.equal(summary.riskTrend.changePercent, 100);
});

test("empty data and missing baselines give a finite sparkline", () => {
  for (const tickets of [[], [ticket(now - 2 * hour)]]) {
    const summary = buildSlaSummary(tickets, now);
    assert.equal(summary.riskTrend.changePercent, null);
    assert.equal(summary.riskTrend.label, "No previous 7-day baseline");
    assert.ok(
      summary.riskTrend.sparkline
        .split(/[ ,]/)
        .every((coordinate) => Number.isFinite(Number(coordinate))),
    );
  }
});

test("advancing the dashboard clock recalculates the SLA buckets", () => {
  const tickets = [ticket(now)];
  assert.equal(buildSlaSummary(tickets, now).countdown.onTrack, 1);
  assert.equal(buildSlaSummary(tickets, now + hour * 0.8).countdown.dueSoon, 1);
  assert.equal(buildSlaSummary(tickets, now + hour).countdown.atRisk, 1);
});
