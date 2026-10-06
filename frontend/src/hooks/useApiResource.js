import { useCallback, useEffect, useRef, useState } from "react";

export function useApiResource(loadData, initialData, errorMessage) {
  const controllerRef = useRef(null);
  const mountedRef = useRef(false);
  const [state, setState] = useState({
    loadData,
    data: initialData,
    isLoading: true,
    error: null,
  });

  const load = useCallback(() => {
    // A refresh supersedes the previous request, so old responses cannot win.
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    return loadData(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setState({ loadData, data, isLoading: false, error: null });
          return data;
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          console.error(errorMessage, error);
          setState((current) => ({
            loadData,
            data: current.loadData === loadData ? current.data : initialData,
            isLoading: false,
            error: errorMessage,
          }));
        }
      });
  }, [loadData, initialData, errorMessage]);

  useEffect(() => {
    mountedRef.current = true;
    load();
    return () => {
      mountedRef.current = false;
      controllerRef.current?.abort();
    };
  }, [load]);

  const refetch = useCallback(() => {
    if (!mountedRef.current) return Promise.resolve();
    setState((current) => ({ ...current, isLoading: true, error: null }));
    return load();
  }, [load]);

  // A different loader (for example, another ticket ID) starts a new resource.
  const isCurrentResource = state.loadData === loadData;
  return {
    data: isCurrentResource ? state.data : initialData,
    isLoading: !isCurrentResource || state.isLoading,
    error: isCurrentResource ? state.error : null,
    refetch,
  };
}
