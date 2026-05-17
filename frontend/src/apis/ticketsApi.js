import { apiClient } from "./apiClient";

export function getTickets() {
  return apiClient("/api/tickets");
}

export function getTicket(ticketId) {
  return apiClient(`/api/tickets/${ticketId}`);
}

export function createTicket(payload) {
  return apiClient("/api/tickets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function analyzeTicket(ticketId) {
  return apiClient(`/api/tickets/${ticketId}/analyze`, {
    method: "POST",
  });
}

export function getLatestTicketDraft(ticketId) {
  return apiClient(`/api/tickets/${ticketId}/draft`);
}