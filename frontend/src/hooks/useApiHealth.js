import { useEffect, useState } from "react";
import { getHealth } from "../apis/healthApi";

export function useApiHealth() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let disposed = false;
    let controller = null;

    async function checkHealth() {
      if (disposed || document.hidden || controller) return;

      const requestController = new AbortController();
      controller = requestController;
      const timeout = setTimeout(() => requestController.abort(), 5_000);

      try {
        const health = await getHealth(requestController.signal);
        if (!disposed) {
          setStatus(health?.status === "ok" ? "connected" : "disconnected");
        }
      } catch {
        if (!disposed) setStatus("disconnected");
      } finally {
        clearTimeout(timeout);
        controller = null;
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 30_000);
    document.addEventListener("visibilitychange", checkHealth);

    return () => {
      disposed = true;
      clearInterval(interval);
      document.removeEventListener("visibilitychange", checkHealth);
      controller?.abort();
    };
  }, []);

  return status;
}
