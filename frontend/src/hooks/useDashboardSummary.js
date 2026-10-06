import { getDashboardSummary } from "../apis/dashboardApi";
import { useApiResource } from "./useApiResource";

export function useDashboardSummary() {
  const { data: summary, ...request } = useApiResource(
    getDashboardSummary,
    null,
    "Failed to load dashboard summary.",
  );
  return { summary, ...request };
}
