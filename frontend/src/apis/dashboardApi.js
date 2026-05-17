import { apiClient } from "./apiClient";

export function getDashboardSummary() {
  return apiClient("/api/dashboard/summary");
}