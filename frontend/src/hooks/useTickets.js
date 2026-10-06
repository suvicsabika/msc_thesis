import { getTickets } from "../apis/ticketsApi";
import { useApiResource } from "./useApiResource";

const emptyTickets = [];

export function useTickets() {
  const { data: tickets, ...request } = useApiResource(
    getTickets,
    emptyTickets,
    "Failed to load tickets.",
  );
  return { tickets, ...request };
}
