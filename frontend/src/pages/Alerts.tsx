import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import type { AlertDetail, AlertList, AlertStatus } from '../types'
import { Card, EmptyState, ErrorBanner, Field, inputCls, KeyValue, Loading, mono, Notice, PageHeader, Pagination, SeverityBadge, SidePanel, StatusBadge, td, th } from '../components/ui'
import { featureLabel, fmtDate, fmtPct, statusLabel } from '../utils/format'

const STATUSES: AlertStatus[] = ['new', 'under_review', 'resolved']

export default function Alerts() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [severity, setSeverity] = useState('')
  const [selected, setSelected] = useState<number | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  useEffect(() => setPage(1), [status, severity])

  const q = new URLSearchParams({ page: String(page), page_size: '25' })
  if (status) q.set('status', status)
  if (severity) q.set('severity', severity)
  const { data, error, loading, reload } = useFetch<AlertList>(`/alerts?${q}`)

  const update = async (id: number, next: AlertStatus) => {
    setActionError(null)
    try { await api.patch(`/alerts/${id}`, { status: next }); reload() } catch (e) { setActionError((e as Error).message) }
  }

  return (
    <>
      <PageHeader title="Detection Alerts" subtitle="Suspicious records predicted by the model. An alert is a prediction awaiting review, not a confirmed incident." />
      {data && (
        <div className="mb-4 flex flex-wrap gap-2 text-[13px]">
          {STATUSES.map((s) => <span key={s} className="rounded border border-line bg-white px-3 py-1.5">{statusLabel(s)}: <strong>{data.status_counts[s]}</strong></span>)}
        </div>
      )}
      <Card className="mb-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Field label="Investigation status">
            <select className={inputCls} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All</option>{STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
            </select>
          </Field>
          <Field label="Severity">
            <select className={inputCls} value={severity} onChange={(e) => setSeverity(e.target.value)}>
              <option value="">All</option><option>High</option><option>Medium</option>
            </select>
          </Field>
        </div>
      </Card>
      {actionError && <div className="mb-3"><ErrorBanner message={actionError} /></div>}
      {error && <ErrorBanner message={error.message} />}
      {loading && !data && <Loading />}
      {data && data.total === 0 && (
        <EmptyState title="No alerts" text="Alerts are created when an analysis classifies records as suspicious. Run an analysis from Dataset Management." action={<Link className="text-primary underline" to="/datasets">Go to Dataset Management</Link>} />
      )}
      {data && data.total > 0 && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead><tr>
                {['Alert', 'Detected', 'Predicted class', 'Severity', 'Confidence', 'Flow ID', 'Status'].map((h) => <th key={h} className={th}>{h}</th>)}
              </tr></thead>
              <tbody>
                {data.items.map((a) => (
                  <tr key={a.id} className="hover:bg-tint">
                    <td className={`${td} ${mono}`}><button className="text-primary underline" onClick={() => setSelected(a.id)}>ALT-{String(a.id).padStart(5, '0')}</button></td>
                    <td className={td}>{fmtDate(a.created_at)}</td>
                    <td className={td}>{a.predicted_class}</td>
                    <td className={td}><SeverityBadge severity={a.severity} /></td>
                    <td className={`${td} ${mono}`}>{fmtPct(a.confidence)}</td>
                    <td className={`${td} ${mono}`}>{a.flow_ref}</td>
                    <td className={td}>
                      <select aria-label={`Status for alert ${a.id}`} className="rounded-md border border-line bg-white px-2 py-1 text-[13px]" value={a.status} onChange={(e) => update(a.id, e.target.value as AlertStatus)}>
                        {STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={data.page_size} total={data.total} onPage={setPage} />
        </Card>
      )}
      {selected !== null && <AlertPanel id={selected} onClose={() => { setSelected(null); reload() }} />}
    </>
  )
}

function AlertPanel({ id, onClose }: { id: number; onClose: () => void }) {
  const { data, error, loading } = useFetch<AlertDetail>(`/alerts/${id}`)
  return (
    <SidePanel title={`Alert ALT-${String(id).padStart(5, '0')}`} onClose={onClose}>
      {loading && <Loading />}
      {error && <ErrorBanner message={error.message} />}
      {data && (
        <div className="space-y-4">
          <Notice tone="warning">{data.note}</Notice>
          <KeyValue rows={[
            ['Predicted class', data.predicted_class],
            ['Severity (policy)', <SeverityBadge severity={data.severity} />],
            ['Confidence', fmtPct(data.confidence)],
            ['Status', <StatusBadge status={data.status} />],
            ['Detected', fmtDate(data.created_at)],
            ['Flow ID', <Link className={`${mono} text-primary underline`} to={`/traffic?analysis=${data.analysis_id}`}>{data.flow_ref}</Link>],
            ['Label in source file', data.actual_label ?? 'Not provided'],
            ['Model', `${data.model_name} (${data.mode})${data.is_synthetic ? ', synthetic data' : ''}`],
          ]} />
          <div>
            <h3 className="mb-2 text-[14px] font-semibold">Relevant feature values</h3>
            <table className="w-full border-collapse"><tbody>
              {Object.entries(data.features).map(([k, v]) => (
                <tr key={k}><td className={td}>{featureLabel(k)}</td><td className={`${td} ${mono} text-right`}>{v == null ? 'missing' : v.toLocaleString('en-US', { maximumFractionDigits: 3 })}</td></tr>
              ))}
            </tbody></table>
          </div>
        </div>
      )}
    </SidePanel>
  )
}
