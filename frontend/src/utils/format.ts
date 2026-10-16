export const fmtInt = (n: number | null | undefined) => (n == null ? '-' : n.toLocaleString('en-US'))
export const fmtPct = (n: number | null | undefined, digits = 1) =>
  n == null ? 'n/a' : `${(n * 100).toFixed(digits)}%`
export const fmtScore = (n: number | null | undefined) => (n == null ? 'n/a' : n.toFixed(3))
export const fmtDate = (iso: string | null | undefined) => {
  if (!iso) return '-'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString()
}
export const fmtBytes = (n: number) =>
  n < 1024 ? `${n} B` : n < 1024 ** 2 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1024 ** 2).toFixed(1)} MB`
export const statusLabel = (s: string) => ({ new: 'New', under_review: 'Under review', resolved: 'Resolved' } as Record<string, string>)[s] ?? s
export const featureLabel = (s: string) => s.replace(/_/g, ' ')
