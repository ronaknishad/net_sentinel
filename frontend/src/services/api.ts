export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, init)
  } catch {
    throw new ApiError('The backend is not reachable. Start it with: python -m uvicorn backend.app.main:app --port 8000', 0)
  }
  if (!res.ok) {
    let message = res.statusText
    try {
      const body = await res.json()
      const d = body.detail
      message = typeof d === 'string' ? d : Array.isArray(d) ? d.map((x: { msg?: string }) => x.msg).join('; ') : message
    } catch { /* keep status text */ }
    throw new ApiError(message, res.status)
  }
  return res.json() as Promise<T>
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body?: unknown) => request<T>(path, json('POST', body ?? {})),
  patch: <T,>(path: string, body: unknown) => request<T>(path, json('PATCH', body)),
  upload: <T,>(path: string, form: FormData) => request<T>(path, { method: 'POST', body: form }),
}

export const MODEL_CHANGED = 'netsentinel:model-changed'
export const notifyModelChanged = () => window.dispatchEvent(new Event(MODEL_CHANGED))
