"""SLA targets for each ticket priority."""

from app.schemas.types import TicketPriority, TicketSla


SLA_BY_PRIORITY: dict[TicketPriority, TicketSla] = {
    "Low": "1 day",
    "Medium": "12h",
    "High": "4h",
    "Very High": "1h",
}


def validate_ticket_sla(priority: TicketPriority, sla: str) -> TicketSla:
    expected = SLA_BY_PRIORITY[priority]
    if sla != expected:
        raise ValueError(f"SLA for {priority} priority must be {expected}.")
    return expected
