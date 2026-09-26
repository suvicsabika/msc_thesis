"""Helpers for building dashboard summaries and trend metrics from ticket records."""

from collections import Counter
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.models.ticket import TicketModel
from app.schemas.dashboard import (
    DashboardKpis,
    DashboardSummary,
    PriorityDistribution,
    SentimentBreakdown,
    SlaCountdown,
    WorkflowActivityItem,
    DashboardTrendMetric,
    DashboardTrends,
)


def normalize_datetime(value: datetime) -> datetime:
    """Convert a naive or aware datetime to UTC for consistent comparisons."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def calculate_change_percent(current_value: int, previous_value: int) -> float | None:
    """Return the percentage change between current and previous values.

    If the previous value is zero, return None to avoid division by zero.
    """

    if previous_value == 0:
        return None

    return round(((current_value - previous_value) / previous_value) * 100, 1)


def get_trend_direction(change_percent: float | None) -> Literal["up", "down", "flat", "none"]:
    """Return a simple trend label based on the percentage change value."""

    if change_percent is None:
        return "none"

    if change_percent > 0:
        return "up"

    if change_percent < 0:
        return "down"

    return "flat"


def build_sparkline_points(values: list[int]) -> str:
    """Generate SVG point coordinates for a small sparkline chart."""

    if not values:
        return "3,26 20,26 32,26 47,26 62,26 78,26 95,26"

    max_value = max(values)
    min_value = min(values)
    value_range = max(max_value - min_value, 1)

    points = []

    for index, value in enumerate(values):
        x = 3 + index * (92 / max(len(values) - 1, 1))
        y = 30 - ((value - min_value) / value_range) * 24
        points.append(f"{round(x, 1)},{round(y, 1)}")

    return " ".join(points)


def count_tickets_in_period(
    tickets: Sequence[TicketModel],
    start_date: datetime,
    end_date: datetime,
    predicate: Callable[[TicketModel], bool],
) -> int:
    """Count tickets matching a predicate within a time window."""

    return sum(
        1
        for ticket in tickets
        if start_date <= normalize_datetime(ticket.createdAt) < end_date
        and predicate(ticket)
    )


def build_daily_counts(
    tickets: Sequence[TicketModel],
    start_date: datetime,
    predicate: Callable[[TicketModel], bool],
) -> list[int]:
    """Build daily ticket counts for the next seven days using a predicate."""

    daily_counts = []

    for day_index in range(7):
        day_start = start_date + timedelta(days=day_index)
        day_end = day_start + timedelta(days=1)

        daily_counts.append(
            count_tickets_in_period(
                tickets=tickets,
                start_date=day_start,
                end_date=day_end,
                predicate=predicate,
            )
        )

    return daily_counts


def build_trend_metric(
    tickets: Sequence[TicketModel],
    now: datetime,
    predicate: Callable[[TicketModel], bool],
    label: str = "last 7 days vs previous 7 days",
) -> DashboardTrendMetric:
    """Create a dashboard trend metric for a ticket subset over a recent period."""
    current_start = now - timedelta(days=7)
    previous_start = now - timedelta(days=14)

    current_value = count_tickets_in_period(
        tickets=tickets,
        start_date=current_start,
        end_date=now,
        predicate=predicate,
    )

    previous_value = count_tickets_in_period(
        tickets=tickets,
        start_date=previous_start,
        end_date=current_start,
        predicate=predicate,
    )

    change_percent = calculate_change_percent(current_value, previous_value)

    if change_percent is None:
        trend_label = "No previous 7-day baseline"
    else:
        trend_label = label

    daily_counts = build_daily_counts(
        tickets=tickets,
        start_date=current_start,
        predicate=predicate,
    )

    return DashboardTrendMetric(
        changePercent=change_percent,
        label=trend_label,
        direction=get_trend_direction(change_percent),
        sparkline=build_sparkline_points(daily_counts),
    )


def build_dashboard_trends(tickets: Sequence[TicketModel]) -> DashboardTrends:
    """Build the dashboard trend section summarizing ticket changes over time."""

    now = datetime.now(timezone.utc)

    return DashboardTrends(
        openTickets=build_trend_metric(
            tickets=tickets,
            now=now,
            predicate=lambda ticket: ticket.status != "Resolved",
        ),
        highPriorityTickets=build_trend_metric(
            tickets=tickets,
            now=now,
            predicate=lambda ticket: ticket.priority in ["High", "Very High"],
        ),
        slaAtRiskTickets=build_trend_metric(
            tickets=tickets,
            now=now,
            predicate=lambda ticket: ticket.slaState == "critical",
        ),
        negativeSentimentTickets=build_trend_metric(
            tickets=tickets,
            now=now,
            predicate=lambda ticket: ticket.sentiment == "Negative",
        ),
    )


def build_dashboard_summary(tickets: Sequence[TicketModel]) -> DashboardSummary:
    """Aggregate ticket data into the full dashboard summary response."""

    priorities = Counter(ticket.priority for ticket in tickets)
    sentiments = Counter(ticket.sentiment for ticket in tickets)
    sla_states = Counter(ticket.slaState for ticket in tickets)
    statuses = Counter(ticket.status for ticket in tickets)

    priority_distribution = PriorityDistribution(
        veryHigh=priorities["Very High"],
        high=priorities["High"],
        medium=priorities["Medium"],
        low=priorities["Low"],
    )

    sentiment_breakdown = SentimentBreakdown(
        negative=sentiments["Negative"],
        neutral=sentiments["Neutral"],
        positive=sentiments["Positive"],
        unknown=0,
    )

    sla_countdown = SlaCountdown(
        atRisk=sla_states["critical"],
        dueSoon=sla_states["warning"],
        onTrack=sla_states["safe"],
    )

    workflow_activity = [
        WorkflowActivityItem(
            ticket=ticket.id,
            text=f"submitted as {ticket.category}",
            time=ticket.updatedAt,
            color="bg-blue-400",
        )
        for ticket in tickets[:4]
    ]

    return DashboardSummary(
        kpis=DashboardKpis(
            openTickets=len(tickets) - statuses["Resolved"],
            highPriorityTickets=priorities["High"],
            slaAtRiskTickets=sla_states["critical"],
            negativeSentimentTickets=sentiments["Negative"],
            resolvedToday=statuses["Resolved"],
        ),
        priorityDistribution=priority_distribution,
        sentimentBreakdown=sentiment_breakdown,
        slaCountdown=sla_countdown,
        workflowActivity=workflow_activity,
        trends=build_dashboard_trends(tickets),
    )
