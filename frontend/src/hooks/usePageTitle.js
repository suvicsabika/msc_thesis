import { useEffect } from "react";

export function usePageTitle(pageTitle) {
  useEffect(() => {
    document.title = `${pageTitle} | MCP Ticket Analyzer`;
  }, [pageTitle]);
}
