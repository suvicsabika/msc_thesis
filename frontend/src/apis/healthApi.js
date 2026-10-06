import { apiClient } from "./apiClient";

export function getHealth(signal) {
  return apiClient("/health", {
    cache: "no-store",
    signal,
  });
}
