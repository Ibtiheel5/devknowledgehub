import { useCallback, useEffect, useRef, useState } from "react";

export function useAsync(asyncFn, deps = [], { immediate = true } = {}) {
  const [state, setState] = useState({
    data: null,
    loading: immediate,
    error: null
  });
  const mountedRef = useRef(false);
  const fnRef = useRef(asyncFn);
  fnRef.current = asyncFn;

  const run = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const data = await fnRef.current();

      if (mountedRef.current) {
        setState({ data, loading: false, error: null });
      }

      return data;
    } catch (error) {
      if (mountedRef.current) {
        setState({ data: null, loading: false, error });
      }

      return null;
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    if (immediate) {
      run();
    }

    return () => {
      mountedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { ...state, reload: run };
}
