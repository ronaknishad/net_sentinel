import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowDown, ArrowUp, Download } from 'lucide-react'
import { api } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import type { Analysis, Flow, FlowDetail, Page } from '../types'
import { Button, Card, ClassBadge, EmptyState, ErrorBanner, Field, inputCls, KeyValue, Loading, mono, Notice, PageHeader, Pagination, SeverityBadge, SidePanel, StatusBadge, td, th } from '../components/ui'
import { featureLabel, fmtDate, fmtInt, fmtPct } from '../utils/format'

const COLUMNS: { key: string; label: string; sortable: boolean }[] = [
  { key: 'flow_ref', label: 'Flow ID', sortable: true },
  { key: 'timestamp', label: 'Timestamp', sortable: true },
  { key: 'protocol', label: 'Protocol', sortable: true },
  { key: 'destination_port', label: 'Dst port', sortable: true },
  { key: 'packets', label: 'Packets', sortable: true },
  { key: 'bytes', label: 'Bytes', sortable: true },
  { key: 'predicted_class', label: 'Predicted classification', sortable: true },
  { key: 'confidence', label: 'Model confidence', sortable: true },
]

export default function TrafficExplorer() {
  const [params, setParams] = useSearchParams()
  const analysisId = params.get('analysis') ?? ''
  const analyses = useFetch<Page<Analysis>>('/analyses?page_size=100')
  const facets = useFetch<{ classes: string[]; protocols: string[] }>(`/flows/facets${analysisId ? `?analysis_id=${analysisId}` : ''}`)

  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState('row_index')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [classification, setClassification] = useState('')
  const [attackClass, setAttackClass] = useState('')
  const [protocol, setProtocol] = useState('')
  const [minConf, setMinConf] = useState('')
  const [maxConf, setMaxConf] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<number | null>(null)

  useEffect(() => setPage(1), [analysisId, classification, attackClass, protocol, minConf, maxConf, search, sortBy, sortDir])

  const query = useMemo(() => {
    const q = new URLSearchParams({ page: String(page), page_size: '25', sort_by: sortBy, sort_dir: sortDir })
    if (analysisId) q.set('analysis_id', analysisId)
    if (classification) q.set('classification', classification)
    if (attackClass) q.set('attack_class', attackClass)
    if (protocol) q.set('protocol', protocol)
    if (minConf) q.set('min_confidence', minConf)
    if (maxConf) q.set('max_confidence', maxConf)
    if (search) q.set('search', search)
    return q.toString()
  }, [page, sortBy, sortDir, analysisId, classification, attackClass, protocol, minConf, maxConf, search])
  const flows = useFetch<Page<Flow>>(`/flows?${query}`)

  const toggleSort = (key: string) => {
    if (sortBy === key) setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    else { setSortBy(key); setSortDir('asc') }
  }
  const hasAny = (flows.data?.total ?? 0) > 0

  return (
    <>
      <PageHeader
        title="Traffic Analysis"
        subtitle="Inspect classified flow records. Classifications are model predictions and are not independently verified."
        actions={analysisId ? (
          <a className="inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-[14px] font-medium hover:bg-tint" href={`/api/exports/analyses/${analysisId}`}>
            <Download size={16} aria-hidden="true" /> Export analysis CSV
          </a>
        ) : undefined}
      />
      <Card className="mb-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Analysis session">
            <select className={inputCls} value={analysisId} onChange={(e) => setParams(e.target.value ? { analysis: e.target.value } : {})}>
              <option value="">All analyses</option>
              {analyses.data?.items.map((a) => <option key={a.id} value={a.id}>#{a.id} {a.name}</option>)}
            </select>
          </Field>
          <Field label="Classification">
            <select className={inputCls} value={classification} onChange={(e) => setClassification(e.target.value)}>
              <option value="">All</option><option value="normal">Normal</option><option value="suspicious">Suspicious</option>
            </select>
          </Field>
          <Field label="Predicted class">
            <select className={inputCls} value={attackClass} onChange={(e) => setAttackClass(e.target.value)}>
              <option value="">All</option>
              {facets.data?.classes.map((c) => <option key={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="Protocol">
            <select className={inputCls} value={protocol} onChange={(e) => setProtocol(e.target.value)}>
              <option value="">All</option>
              {facets.data?.protocols.map((p) => <option key={p}>{p}</option>)}
            </select>
          </Field>
          <Field label="Min confidence (0-1)">
            <input className={inputCls} type="number" min={0} max={1} step={0.05} value={minConf} onChange={(e) => setMinConf(e.target.value)} />
          </Field>
          <Field label="Max confidence (0-1)">
            <input className={inputCls} type="number" min={0} max={1} step={0.05} value={maxConf} onChange={(e) => setMaxConf(e.target.value)} />
          </Field>
          <form className="flex items-end gap-2 sm:col-span-2" onSubmit={(e) => { e.preventDefault(); setSearch(searchInput.trim()) }}>
            <div className="flex-1"><Field label="Search flow ID or destination port">
              <input className={inputCls} value={searchInput} maxLength={100} onChange={(e) => setSearchInput(e.target.value)} />
            </Field></div>
            <Button type="submit">Search</Button>
            <Button variant="secondary" onClick={() => { setSearchInput(''); setSearch(''); setClassification(''); setAttackClass(''); setProtocol(''); setMinConf(''); setMaxConf('') }}>Reset</Button>
          </form>
        </div>
      </Card>

      {flows.error && <ErrorBanner message={flows.error.message} />}
      {flows.loading && !flows.data && <Loading />}
      {flows.data && !hasAny && (
        <EmptyState title="No flows to show" text="Run an analysis from Dataset Management, or adjust the filters." action={<Link className="text-primary underline" to="/datasets">Go to Dataset Management</Link>} />
      )}
      {flows.data && hasAny && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {COLUMNS.map((c) => (
                    <th key={c.key} className={th} aria-sort={sortBy === c.key ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                      <button className="inline-flex items-center gap-1" onClick={() => toggleSort(c.key)}>
                        {c.label}
                        {sortBy === c.key && (sortDir === 'asc' ? <ArrowUp size={12} aria-hidden="true" /> : <ArrowDown size={12} aria-hidden="true" />)}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {flows.data.items.map((f) => (
                  <tr key={f.id} className="cursor-pointer hover:bg-tint" onClick={() => setSelected(f.id)}>
                    <td className={`${td} ${mono}`}>
                      <button className="text-primary underline" onClick={(e) => { e.stopPropagation(); setSelected(f.id) }}>{f.flow_ref}</button>
                    </td>
                    <td className={`${td} ${mono}`}>{f.timestamp ? fmtDate(f.timestamp) : '-'}</td>
                    <td className={td}>{f.protocol ?? '-'}</td>
                    <td className={`${td} ${mono}`}>{f.destination_port ?? '-'}</td>
                    <td className={`${td} ${mono}`}>{fmtInt(f.packets)}</td>
                    <td className={`${td} ${mono}`}>{fmtInt(f.bytes)}</td>
                    <td className={td}><ClassBadge cls={f.predicted_class} suspicious={f.is_suspicious} severity={f.severity} /></td>
                    <td className={`${td} ${mono}`}>{fmtPct(f.confidence)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={flows.data.page_size} total={flows.data.total} onPage={setPage} />
        </Card>
      )}
      <SingleRecord />
      {selected !== null && <FlowPanel id={selected} onClose={() => setSelected(null)} />}
    </>
  )
}

function FlowPanel({ id, onClose }: { id: number; onClose: () => void }) {
  const { data, error, loading } = useFetch<FlowDetail>(`/flows/${id}`)
  return (
    <SidePanel title="Flow detail" onClose={onClose}>
      {loading && <Loading />}
      {error && <ErrorBanner message={error.message} />}
      {data && (
        <div className="space-y-4">
          <KeyValue rows={[
            ['Flow ID', <span className={mono}>{data.flow_ref}</span>],
            ['Timestamp', data.timestamp ? fmtDate(data.timestamp) : '-'],
            ['Prediction', <ClassBadge cls={data.predicted_class} suspicious={data.is_suspicious} severity={data.severity} />],
            ['Confidence', fmtPct(data.confidence)],
            ['Severity (policy)', <SeverityBadge severity={data.severity} />],
            ['Label in source file', data.actual_label ?? 'Not provided'],
            ['Model', `${data.model.model_name} (${data.model.mode})${data.model.is_synthetic ? ', synthetic training data' : ''}`],
            ['Alert', data.alert ? <span className="inline-flex items-center gap-2"><StatusBadge status={data.alert.status} /><Link className="text-primary underline" to="/alerts">Open alerts</Link></span> : 'None'],
          ]} />
          <Notice>Confidence is the model's estimate for the predicted class. It is not a calibrated risk score and does not confirm an intrusion.</Notice>
          <div>
            <h3 className="mb-2 text-[14px] font-semibold">Model input features</h3>
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

function SingleRecord() {
  const samples = useFetch<{ items: { synthetic_label: string; record: Record<string, number>; note: string }[] }>('/predictions/samples')
  const [text, setText] = useState('')
  const [save, setSave] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [result, setResult] = useState<{ prediction: { predicted_class: string; is_suspicious: boolean; severity: string; confidence: number | null }; message: string; probability_note: string; analysis_id: number | null } | null>(null)

  const submit = async () => {
    setErr(null); setResult(null)
    let record: unknown
    try { record = JSON.parse(text) } catch { setErr('The record is not valid JSON.'); return }
    if (typeof record !== 'object' || record === null || Array.isArray(record)) { setErr('The record must be a JSON object of feature names and numbers.'); return }
    setBusy(true)
    try { setResult(await api.post('/predictions', { record, save })) } catch (e) { setErr((e as Error).message) } finally { setBusy(false) }
  }
  return (
    <Card title="Classify a single flow" className="mt-4">
      <p className="mb-3 text-muted">Enter one flow using the supported feature names (see System Status), or load a synthetic example generated by documented rules.</p>
      <div className="mb-2 flex flex-wrap gap-2">
        {samples.data?.items.map((s) => (
          <Button key={s.synthetic_label} variant="secondary" onClick={() => setText(JSON.stringify(s.record, null, 2))}>Load synthetic {s.synthetic_label}</Button>
        ))}
      </div>
      <label className="block text-[12px] text-muted"><span className="mb-1 block">Flow record (JSON)</span>
        <textarea className={`${inputCls} ${mono} h-40`} value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} />
      </label>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Button onClick={submit} disabled={busy || !text.trim()}>{busy ? 'Classifying...' : 'Classify flow'}</Button>
        <label className="flex items-center gap-2 text-[13px]"><input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} /> Save as an analysis (creates an alert if suspicious)</label>
      </div>
      {err && <div className="mt-3"><ErrorBanner message={err} /></div>}
      {result && (
        <div className="mt-3 space-y-2">
          <Notice tone="normal">{result.message}</Notice>
          <KeyValue rows={[
            ['Predicted classification', <ClassBadge cls={result.prediction.predicted_class} suspicious={result.prediction.is_suspicious} severity={result.prediction.severity} />],
            ['Model confidence', fmtPct(result.prediction.confidence)],
            ['Saved', result.analysis_id ? <Link className="text-primary underline" to={`/traffic?analysis=${result.analysis_id}`}>Analysis #{result.analysis_id}</Link> : 'No'],
          ]} />
          <p className="text-[12px] text-muted">{result.probability_note}</p>
        </div>
      )}
    </Card>
  )
}
