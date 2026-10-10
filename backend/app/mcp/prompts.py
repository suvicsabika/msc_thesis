"""Detailed triage instructions served through MCP prompts."""


def build_ticket_triage_prompt(ticket_json: str) -> str:
    """Build a triage prompt containing the ticket JSON."""
    return f"""
Analyze this support ticket and produce a complete triage decision.

You must decide:
- category
- sentiment
- customer intent
- priority
- SLA state and SLA label
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

Allowed customer intents:
- Issue report
- Billing question
- How-to request
- Feature request
- General inquiry

Priority rules:
- Very High: production outage, blocked business operation, \
security-sensitive issue, critical customer impact, or urgent blocker.
- High: important customer-impacting issue that should be handled \
quickly, but is not a full production outage.
- Medium: customer productivity may be affected, but the issue is \
not urgent or business-critical.
- Low: informational, general, how-to, feature request, or low-risk request.

SLA policy:
- Low: 1 day
- Medium: 12h
- High: 4h
- Very High: 1h

If the ticket contains words like "critical", "urgent", "blocked", \
"blocking", "production", "down", or "cannot work", do not choose Low.
If the ticket is a negative Bug, API, Access, or Performance issue, \
choose at least Medium.

Ticket JSON:
{ticket_json}
""".strip()
