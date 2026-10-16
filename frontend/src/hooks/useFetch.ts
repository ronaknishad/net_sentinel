import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '../services/api'

export function useFetch<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(path !== null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (path === null) { setData(null); setLoading(false); return }
    let cancelled = false
    setLoading(true)
    api.get<T>(path)
      .then((d) => { if (!cancelled) { setData(d); setError(null) } })
      .catch((e: ApiError) => { if (!cancelled) { setError(e); setData(null) } })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [path, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { data, error, loading, reload }
}
