"""Prompt templates for OpenAI ticket triage.

This module defines the system prompt and helper to build the ticket triage
prompt sent to the OpenAI Responses API.
"""

TRIAGE_SYSTEM_PROMPT = """
You are a customer support ticket triage assistant.

Analyze the ticket conservatively and only use the information provided.
Do not invent facts, technical root causes, refunds, deadlines, or commitments.
The response draft must be safe, polite, concise, and must require human approval.
Return only the structured result requested by the schema.
"""


def build_ticket_triage_prompt(ticket_json: str) -> str:
    """Build the user prompt that contains the ticket JSON for OpenAI."""
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
- Very High: production outage, blocked business operation, security-sensitive issue, critical customer impact, or urgent blocker.
- High: important customer-impacting issue that should be handled quickly, but is not a full production outage.
- Medium: customer productivity may be affected, but the issue is not urgent or business-critical.
- Low: informational, general, how-to, feature request, or low-risk request.

SLA policy:
- Low: 1 day
- Medium: 12h
- High: 4h
- Very High: 1h

If the ticket contains words like "critical", "urgent", "blocked", "blocking", "production", "down", or "cannot work", do not choose Low.
If the ticket is a negative Bug, API, Access, or Performance issue, choose at least Medium.

Ticket JSON:
{ticket_json}
""".strip()