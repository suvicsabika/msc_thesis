from typing import Literal

from pydantic import BaseModel


class DashboardKpis(BaseModel):
    openTickets: int
    highPriorityTickets: int
    veryHighPriorityTickets: int
    negativeSentimentTickets: int
    resolvedToday: int


class PriorityDistribution(BaseModel):
    veryHigh: int
    high: int
    medium: int
    low: int


class SentimentBreakdown(BaseModel):
    negative: int
    neutral: int
    positive: int
    unknown: int


class WorkflowActivityItem(BaseModel):
    ticket: str
    text: str
    time: str
    color: str


class DashboardTrendMetric(BaseModel):
    changePercent: float | None
    label: str
    direction: Literal["up", "down", "flat", "none"]
    sparkline: str


class DashboardTrends(BaseModel):
    openTickets: DashboardTrendMetric
    highPriorityTickets: DashboardTrendMetric
    veryHighPriorityTickets: DashboardTrendMetric
    negativeSentimentTickets: DashboardTrendMetric


class DashboardSummary(BaseModel):
    kpis: DashboardKpis
    priorityDistribution: PriorityDistribution
    sentimentBreakdown: SentimentBreakdown
    workflowActivity: list[WorkflowActivityItem]
    trends: DashboardTrends
