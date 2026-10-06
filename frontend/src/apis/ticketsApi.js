import { apiClient } from "./apiClient";

export function getTickets(signal) {
  return apiClient("/tickets", { signal });
}

export function getTicket(ticketId, signal) {
  return apiClient(`/tickets/${encodeURIComponent(ticketId)}`, { signal });
}

export function createTicket(payload) {
  return apiClient("/tickets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function analyzeTicket(ticketId) {
  return apiClient(`/tickets/${encodeURIComponent(ticketId)}/analyze`, {
    method: "POST",
  });
}

export function getLatestTicketDraft(ticketId, signal) {
  return apiClient(`/tickets/${encodeURIComponent(ticketId)}/draft`, {
    signal,
  });
}
