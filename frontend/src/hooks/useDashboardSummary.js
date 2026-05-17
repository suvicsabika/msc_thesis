import { useCallback, useEffect, useState } from "react";
import { getDashboardSummary } from "../apis/dashboardApi";

export function useDashboardSummary() {
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadDashboardSummary = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const result = await getDashboardSummary();
      setSummary(result);
    } catch (err) {
      console.error("Failed to load dashboard summary:", err);
      setError("Failed to load dashboard summary.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardSummary();
  }, [loadDashboardSummary]);

  return {
    summary,
    isLoading,
    error,
    refetch: loadDashboardSummary,
  };
}