import { apiClient } from "./apiClient";

export function getDashboardSummary(signal) {
  return apiClient("/dashboard/summary", { signal });
}
