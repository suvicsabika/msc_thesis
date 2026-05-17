"""Helpers for building dashboard summaries and trend metrics from ticket records."""

from datetime import datetime, timedelta, timezone
from typing import Callable, Literal

from app.schemas.dashboard import (
    DashboardKpis,
    DashboardSummary,
    PriorityDistribution,
    SentimentBreakdown,
    SlaCountdown,
    WorkflowActivityItem,
    DashboardTrendMetric, 
    DashboardTrends
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
    tickets,
    start_date: datetime,
    end_date: datetime,
    predicate: Callable,
) -> int:
    """Count tickets matching a predicate within a time window."""

    return len(
        [
            ticket
            for ticket in tickets
            if start_date <= normalize_datetime(ticket.createdAt) < end_date
            and predicate(ticket)
        ]
    )


def build_daily_counts(
    tickets,
    start_date: datetime,
    predicate: Callable,
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
    tickets,
    now: datetime,
    predicate: Callable,
    label: str,
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


def build_dashboard_trends(tickets) -> DashboardTrends:
    """Build the dashboard trend section summarizing ticket changes over time."""

    now = datetime.now(timezone.utc)

    return DashboardTrends(
        openTickets=build_trend_metric(
            tickets=tickets,
            now=now,
            predicate=lambda ticket: ticket.status != "Resolved",
            label="last 7 days vs previous 7 days",
        ),
        highPriorityTickets=build_trend_metric(
            tickets=tickets,
            now=now,
            predicate=lambda ticket: ticket.priority in ["High", "Very High"],
            label="last 7 days vs previous 7 days",
        ),
        slaAtRiskTickets=build_trend_metric(
            tickets=tickets,
            now=now,
            predicate=lambda ticket: ticket.slaState == "critical",
            label="last 7 days vs previous 7 days",
        ),
        negativeSentimentTickets=build_trend_metric(
            tickets=tickets,
            now=now,
            predicate=lambda ticket: ticket.sentiment == "Negative",
            label="last 7 days vs previous 7 days",
        ),
    )

def build_dashboard_summary(tickets) -> DashboardSummary:
    """Aggregate ticket data into the full dashboard summary response."""

    open_tickets = [
        ticket for ticket in tickets
        if ticket.status != "Resolved"
    ]

    high_priority_tickets = [
        ticket for ticket in tickets
        if ticket.priority == "High"
    ]

    sla_at_risk_tickets = [
        ticket for ticket in tickets
        if ticket.slaState == "critical"
    ]

    negative_sentiment_tickets = [
        ticket for ticket in tickets
        if ticket.sentiment == "Negative"
    ]

    resolved_tickets = [
        ticket for ticket in tickets
        if ticket.status == "Resolved"
    ]

    priority_distribution = PriorityDistribution(
        veryHigh=len([ticket for ticket in tickets if ticket.priority == "Very High"]),
        high=len([ticket for ticket in tickets if ticket.priority == "High"]),
        medium=len([ticket for ticket in tickets if ticket.priority == "Medium"]),
        low=len([ticket for ticket in tickets if ticket.priority == "Low"]),
    )

    sentiment_breakdown = SentimentBreakdown(
        negative=len([ticket for ticket in tickets if ticket.sentiment == "Negative"]),
        neutral=len([ticket for ticket in tickets if ticket.sentiment == "Neutral"]),
        positive=len([ticket for ticket in tickets if ticket.sentiment == "Positive"]),
        unknown=0,
    )

    sla_countdown = SlaCountdown(
        atRisk=len([ticket for ticket in tickets if ticket.slaState == "critical"]),
        dueSoon=len([ticket for ticket in tickets if ticket.slaState == "warning"]),
        onTrack=len([ticket for ticket in tickets if ticket.slaState == "safe"]),
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
            openTickets=len(open_tickets),
            highPriorityTickets=len(high_priority_tickets),
            slaAtRiskTickets=len(sla_at_risk_tickets),
            negativeSentimentTickets=len(negative_sentiment_tickets),
            resolvedToday=len(resolved_tickets),
        ),
        priorityDistribution=priority_distribution,
        sentimentBreakdown=sentiment_breakdown,
        slaCountdown=sla_countdown,
        workflowActivity=workflow_activity,
        trends=build_dashboard_trends(tickets)
    )