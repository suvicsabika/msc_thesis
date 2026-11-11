"""Detailed triage instructions shared by both transports."""

from app.core.ticket_policy import SLA_BY_PRIORITY


def build_ticket_triage_prompt(ticket_id: str) -> str:
    """Describe the task without loading ticket data."""
    sla_policy = "\n".join(
        f"- {priority}: {sla}" for priority, sla in SLA_BY_PRIORITY.items()
    )
    return f"""
Analyze support ticket {ticket_id} and save a complete triage decision.

Discover the appropriate operations from the supplied MCP catalog.
First request the current ticket's original content through
read_mcp_resource. Read other permitted resources if they help the task.
Then use the available MCP tools to save the category, sentiment,
priority with SLA, and customer response draft. Choose the tool order
yourself. Call each saving tool once and inspect its result.
Finish only after all four saves succeed. Your final structured decision
must exactly match the values and reasons submitted to those tools.
Existing classifications and drafts are prior state, not ground truth.

You must decide:
- category
- sentiment
- priority
- SLA label
- customer response draft
- short reasoning summary

Allowed categories:
- General
- Access
- Billing
- API
- Bug
- Feature Request
- Performance

Allowed sentiments:
- Negative
- Neutral
- Positive

Priority rules:
- Very High: production outage, blocked business operation, \
security-sensitive issue, critical customer impact, or urgent blocker.
- High: important customer-impacting issue that should be handled \
quickly, but is not a full production outage.
- Medium: customer productivity may be affected, but the issue is \
not urgent or business-critical.
- Low: informational, general, how-to, feature request, or low-risk request.

Sentiment rules:
- Negative: the customer expresses dissatisfaction, frustration,
  disappointment, or another explicitly negative attitude.
- Neutral: factual reporting or a request without a clearly expressed
  positive or negative attitude. A technical issue alone does not
  necessarily imply negative sentiment.
- Positive: the customer expresses satisfaction, appreciation, or praise.

Priority assessment:
- Base priority primarily on the stated business impact, scope,
  urgency, and availability of a workaround.
- High: a core function is unavailable or materially impaired,
  with significant customer impact and no stated usable workaround,
  but without evidence of a critical production-wide outage.
- Medium: functionality is partially impaired, the impact is limited,
  or a usable workaround is stated.
- Do not invent business impact, urgency, or a workaround.
- If impact is unclear, explain the uncertainty in the reasoning.

Category boundaries:
- Performance: the main problem is slowness, latency, timeouts,
  or degraded throughput, including when an API is involved.
- API: the main problem concerns API authentication, request format,
  integration behavior, rate limits, or API-specific functionality.

SLA policy:
{sla_policy}

If the ticket contains words like "critical", "urgent", "blocked", \
"blocking", "production", "down", or "cannot work", do not choose Low.
If the ticket is a negative Bug, API, Access, or Performance issue, \
choose at least Medium.

""".strip()
