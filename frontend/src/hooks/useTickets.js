import { useCallback, useEffect, useState } from "react";
import { getTickets } from "../apis/ticketsApi";

export function useTickets() {
  const [tickets, setTickets] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadTickets = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const result = await getTickets();
      setTickets(result);
    } catch (err) {
      console.error("Failed to load tickets:", err);
      setError("Failed to load tickets.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTickets();
  }, [loadTickets]);
  
  return {
    tickets,
    isLoading,
    error,
    refetch: loadTickets,
  };
}