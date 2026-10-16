import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, notifyModelChanged } from '../services/api'
import { useFetch } from '../hooks/useFetch'
import type { Analysis, Dataset, ModelStatus, TrainingRun } from '../types'
import { Badge, Button, Card, EmptyState, ErrorBanner, Field, inputCls, KeyValue, Loading, mono, Notice, PageHeader, td, th } from '../components/ui'
import { fmtBytes, fmtDate, fmtInt, featureLabel } from '../utils/format'

export default function DatasetManagement() {
  const list = useFetch<{ items: Dataset[] }>('/datasets')
  const model = useFetch<ModelStatus>('/model/status')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState<{ tone: 'normal' | 'critical'; text: string } | null>(null)

  const items = list.data?.items ?? []
  useEffect(() => { if (selectedId === null && items.length) setSelectedId(items[0].id) }, [items, selectedId])
  const selected = items.find((d) => d.id === selectedId) ?? null

  const run = async (key: string, fn: () => Promise<string>) => {
    setBusy(key); setMessage(null)
    try { setMessage({ tone: 'normal', text: await fn() }) } catch (e) { setMessage({ tone: 'critical', text: (e as Error).message }) } finally { setBusy(null) }
  }

  const [file, setFile] = useState<File | null>(null)
  const [labelCol, setLabelCol] = useState('')
  const [synthetic, setSynthetic] = useState(false)
  const upload = () => file && run('upload', async () => {
    const form = new FormData()
    form.append('file', file)
    if (labelCol.trim()) form.append('label_column', labelCol.trim())
    form.append('is_synthetic', String(synthetic))
    const d = await api.upload<Dataset>('/datasets/upload', form)
    list.reload(); setSelectedId(d.id); setFile(null)
    return d.is_valid ? `Dataset validation completed. ${fmtInt(d.row_count)} records imported.` : 'The file was imported but failed validation. Review the errors below.'
  })
  const loadSample = () => run('sample', async () => {
    const d = await api.post<Dataset>('/datasets/sample')
    list.reload(); setSelectedId(d.id)
    return `Synthetic sample loaded: ${fmtInt(d.row_count)} records. This data is synthetic and not a real benchmark.`
  })

  return (
    <>
      <PageHeader title="Dataset Management" subtitle="Import and validate labelled flow data, train a model, then analyse traffic. Files are parsed as data only." />
      {message && <div className="mb-4">{message.tone === 'critical' ? <ErrorBanner message={message.text} /> : <Notice tone="normal">{message.text}</Notice>}</div>}

      <Card title="Import traffic data">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Field label="CSV file (max 200 MB)"><input className={inputCls} type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></Field>
          <Field label="Label column (optional, auto-detected)"><input className={inputCls} value={labelCol} onChange={(e) => setLabelCol(e.target.value)} placeholder="Label" /></Field>
          <label className="flex items-end gap-2 pb-2 text-[13px]"><input type="checkbox" checked={synthetic} onChange={(e) => setSynthetic(e.target.checked)} /> This file contains synthetic data</label>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button onClick={upload} disabled={!file || busy !== null}>{busy === 'upload' ? 'Importing...' : 'Import and validate'}</Button>
          <Button variant="secondary" onClick={loadSample} disabled={busy !== null}>{busy === 'sample' ? 'Loading...' : 'Load bundled synthetic sample'}</Button>
        </div>
        <p className="mt-2 text-[12px] text-muted">Large public datasets such as CIC-IDS2017 are not downloaded automatically. See datasets/README.md for size and licence notes.</p>
      </Card>

      {list.loading && !list.data && <Loading />}
      {list.error && <div className="mt-4"><ErrorBanner message={list.error.message} /></div>}
      {list.data && items.length === 0 && (
        <div className="mt-4"><EmptyState title="No datasets imported" text="Import a CSV above, or load the bundled synthetic sample to try the full workflow offline." /></div>
      )}
      {items.length > 0 && (
        <Card title="Imported datasets" className="mt-4">
          <div className="overflow-x-auto"><table className="w-full border-collapse">
            <thead><tr>{['', 'Name', 'Rows', 'Size', 'Validation', 'Imported'].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
            <tbody>{items.map((d) => (
              <tr key={d.id} className={d.id === selectedId ? 'bg-tint' : ''}>
                <td className={td}><input type="radio" name="dataset" aria-label={`Select ${d.name}`} checked={d.id === selectedId} onChange={() => setSelectedId(d.id)} /></td>
                <td className={td}>{d.name}{d.is_synthetic && <> <Badge tone="warning">Synthetic</Badge></>}</td>
                <td className={`${td} ${mono}`}>{fmtInt(d.row_count)}</td><td className={td}>{fmtBytes(d.size_bytes)}</td>
                <td className={td}><Badge tone={d.is_valid ? 'normal' : 'critical'}>{d.is_valid ? 'Valid' : 'Failed validation'}</Badge></td>
                <td className={td}>{fmtDate(d.created_at)}</td>
              </tr>))}</tbody>
          </table></div>
        </Card>
      )}
      {selected && <DatasetDetail key={selected.id} ds={selected} onChanged={list.reload} />}
      {selected && <Workflow ds={selected} modelLoaded={!!model.data?.loaded} run={run} busy={busy} />}
    </>
  )
}

function DatasetDetail({ ds, onChanged }: { ds: Dataset; onChanged: () => void }) {
  const v = ds.validation
  const preview = useFetch<{ columns: string[]; rows: Record<string, unknown>[] }>(`/datasets/${ds.id}/preview?rows=8`)
  const [label, setLabel] = useState(ds.label_column ?? '')
  const [overrides, setOverrides] = useState<Record<string, string>>(ds.column_overrides)
  const [err, setErr] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const mappedColumns = new Set(Object.values(v.mapped_features))

  const revalidate = async () => {
    setSaving(true); setErr(null)
    try { await api.post(`/datasets/${ds.id}/validate`, { label_column: label || null, column_overrides: overrides }); onChanged() }
    catch (e) { setErr((e as Error).message) } finally { setSaving(false) }
  }
  const classes = Object.entries(v.class_distribution)
  const dataIssues: [string, string][] = [
    ...Object.entries(v.missing_values).map(([k, n]) => [`Missing: ${featureLabel(k)}`, fmtInt(n)] as [string, string]),
    ...Object.entries(v.infinite_values).map(([k, n]) => [`Infinite: ${featureLabel(k)}`, fmtInt(n)] as [string, string]),
    ...Object.entries(v.non_numeric_values).map(([k, n]) => [`Non-numeric: ${featureLabel(k)}`, fmtInt(n)] as [string, string]),
  ]

  return (
    <Card title={`Validation: ${ds.name}`} className="mt-4">
      {v.errors.map((e) => <div key={e} className="mb-2"><ErrorBanner message={e} /></div>)}
      {v.warnings.map((w) => <div key={w} className="mb-2"><Notice tone="warning">{w}</Notice></div>)}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="space-y-4">
          <KeyValue rows={[
            ['Rows', fmtInt(v.rows)], ['Columns', fmtInt(v.columns)], ['File size', fmtBytes(ds.size_bytes)],
            ['Label column', v.label_column ?? 'Not detected'], ['Duplicate rows', fmtInt(v.duplicate_rows)],
            ['Rows without a label', fmtInt(v.missing_labels)],
          ]} />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Label column">
              <select className={inputCls} value={label} onChange={(e) => setLabel(e.target.value)}>
                <option value="">Auto-detect</option>{ds.columns.map((c) => <option key={c}>{c}</option>)}
              </select>
            </Field>
          </div>
          <div>
            <h3 className="mb-2 text-[14px] font-semibold">Feature mapping</h3>
            <table className="w-full border-collapse"><thead><tr><th className={th}>Supported feature</th><th className={th}>CSV column</th></tr></thead>
              <tbody>
                {Object.entries(v.mapped_features).map(([f, c]) => <tr key={f}><td className={`${td} ${mono}`}>{f}</td><td className={`${td} ${mono}`}>{c}</td></tr>)}
                {v.missing_features.map((f) => (
                  <tr key={f}><td className={`${td} ${mono}`}>{f}</td><td className={td}>
                    <select aria-label={`CSV column for ${f}`} className="w-full rounded-md border border-line bg-white px-2 py-1 text-[13px]" value={overrides[f] ?? ''}
                      onChange={(e) => setOverrides((o) => { const n = { ...o }; if (e.target.value) n[f] = e.target.value; else delete n[f]; return n })}>
                      <option value="">Not mapped</option>
                      {ds.columns.filter((c) => !mappedColumns.has(c) && c !== v.label_column).map((c) => <option key={c}>{c}</option>)}
                    </select></td></tr>
                ))}
              </tbody></table>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={revalidate} disabled={saving}>{saving ? 'Validating...' : 'Re-validate with these settings'}</Button>
            {err && <span className="text-[13px] text-crit" role="alert">{err}</span>}
          </div>
        </div>
        <div className="space-y-4">
          <div>
            <h3 className="mb-2 text-[14px] font-semibold">Class distribution</h3>
            {classes.length ? (
              <table className="w-full border-collapse"><thead><tr><th className={th}>Class</th><th className={th}>Rows</th><th className={th}>Share</th></tr></thead>
                <tbody>{classes.map(([c, n]) => <tr key={c}><td className={td}>{c}</td><td className={`${td} ${mono}`}>{fmtInt(n)}</td><td className={`${td} ${mono}`}>{((n / (v.rows - v.missing_labels || 1)) * 100).toFixed(1)}%</td></tr>)}</tbody></table>
            ) : <p className="text-muted">No labels available.</p>}
          </div>
          <div>
            <h3 className="mb-2 text-[14px] font-semibold">Missing and invalid values (mapped features)</h3>
            {dataIssues.length ? <table className="w-full border-collapse"><tbody>{dataIssues.map(([k, n]) => <tr key={k}><td className={td}>{k}</td><td className={`${td} ${mono} text-right`}>{n}</td></tr>)}</tbody></table> : <p className="text-muted">None found.</p>}
          </div>
          <div>
            <h3 className="mb-2 text-[14px] font-semibold">Columns not used as model input</h3>
            {v.unsupported_columns.length ? (
              <div className="max-h-48 overflow-y-auto"><table className="w-full border-collapse"><tbody>
                {v.unsupported_columns.map((u) => <tr key={u.column}><td className={`${td} ${mono}`}>{u.column}</td><td className={`${td} text-muted`}>{u.reason}</td></tr>)}
              </tbody></table></div>
            ) : <p className="text-muted">None.</p>}
          </div>
        </div>
      </div>
      <div className="mt-6">
        <h3 className="mb-2 text-[14px] font-semibold">Preview (first rows)</h3>
        {preview.loading && <Loading />}
        {preview.error && <ErrorBanner message={preview.error.message} />}
        {preview.data && (
          <div className="overflow-x-auto"><table className="border-collapse">
            <thead><tr>{preview.data.columns.map((c) => <th key={c} className={th}>{c}</th>)}</tr></thead>
            <tbody>{preview.data.rows.map((r, i) => <tr key={i}>{preview.data!.columns.map((c) => <td key={c} className={`${td} ${mono}`}>{r[c] == null ? '' : String(r[c])}</td>)}</tr>)}</tbody>
          </table></div>
        )}
      </div>
    </Card>
  )
}

function Workflow({ ds, modelLoaded, run, busy }: { ds: Dataset; modelLoaded: boolean; run: (k: string, fn: () => Promise<string>) => void; busy: string | null }) {
  const [mode, setMode] = useState<'multiclass' | 'binary'>('multiclass')
  const [confirm, setConfirm] = useState(false)
  const [job, setJob] = useState<TrainingRun | null>(null)
  const [synthRows, setSynthRows] = useState(500)
  const history = useFetch<{ items: TrainingRun[] }>('/models/train')

  useEffect(() => {
    if (job?.status !== 'running') return
    const t = setInterval(async () => {
      try {
        const next = await api.get<TrainingRun>(`/models/train/${job.id}`)
        setJob(next)
        if (next.status !== 'running') { notifyModelChanged(); history.reload() }
      } catch { /* retry on next tick */ }
    }, 2000)
    return () => clearInterval(t)
  }, [job?.id, job?.status])

  const train = () => run('train', async () => {
    const r = await api.post<TrainingRun>('/models/train', { dataset_id: ds.id, mode, confirm: true })
    setJob(r); setConfirm(false)
    return 'Training started. This runs in the background; progress is shown below.'
  })
  const analyse = () => run('analyse', async () => {
    const a = await api.post<Analysis>('/analyses', { source: 'dataset', dataset_id: ds.id })
    return `${fmtInt(a.total_flows)} records processed. ${fmtInt(a.suspicious_count)} records classified as suspicious.${a.rejected_count ? ` ${a.rejected_count} rows rejected.` : ''}`
  })
  const synth = () => run('synth', async () => {
    const a = await api.post<Analysis>('/analyses', { source: 'synthetic', synthetic_rows: synthRows })
    return `${fmtInt(a.total_flows)} synthetic records processed. ${fmtInt(a.suspicious_count)} records classified as suspicious.`
  })

  return (
    <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
      <Card title="Train a model">
        {!ds.is_valid && <Notice tone="critical">This dataset failed validation and cannot be used for training.</Notice>}
        <p className="mb-3 text-[13px] text-muted">Random Forest, Decision Tree and Logistic Regression are trained on the same stratified split and compared. The best F1 is saved.</p>
        <Field label="Classification mode">
          <select className={inputCls} value={mode} onChange={(e) => setMode(e.target.value as 'multiclass' | 'binary')}>
            <option value="multiclass">Multiclass (Normal and each attack type in the data)</option>
            <option value="binary">Binary (Normal vs Suspicious)</option>
          </select>
        </Field>
        <label className="mt-3 flex items-start gap-2 text-[13px]">
          <input type="checkbox" className="mt-1" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} />
          <span>I confirm training on {fmtInt(ds.row_count)} rows ({fmtBytes(ds.size_bytes)}). It may take several minutes on large files and replaces the active model.</span>
        </label>
        <div className="mt-3"><Button onClick={train} disabled={!confirm || !ds.is_valid || busy !== null || job?.status === 'running'}>
          {job?.status === 'running' ? 'Training in progress...' : 'Train model'}</Button></div>
        {job && (
          <div className="mt-3" aria-live="polite">
            {job.status === 'running' && <Notice>Training is running (started {fmtDate(job.started_at)}). You can leave this page; the job continues.</Notice>}
            {job.status === 'completed' && <Notice tone="normal">Training completed. Model {job.model_id} is loaded. <Link className="underline" to="/evaluation">View evaluation</Link></Notice>}
            {job.status === 'failed' && <ErrorBanner message={job.error ?? 'Training failed.'} />}
          </div>
        )}
        {history.data && history.data.items.length > 0 && (
          <details className="mt-3 text-[13px]"><summary className="cursor-pointer text-muted">Training history</summary>
            <table className="mt-2 w-full border-collapse"><tbody>{history.data.items.slice(0, 5).map((r) => (
              <tr key={r.id}><td className={td}>#{r.id}</td><td className={td}>{r.mode}</td><td className={td}>{r.status}</td><td className={`${td} ${mono}`}>{r.model_id ?? r.error?.slice(0, 40) ?? ''}</td></tr>))}</tbody></table>
          </details>
        )}
      </Card>
      <Card title="Analyse traffic">
        {!modelLoaded && <div className="mb-3"><Notice tone="warning">No model is loaded. Train a model first.</Notice></div>}
        <p className="mb-3 text-[13px] text-muted">Classify every flow in the selected dataset with the active model. Results appear in Traffic Analysis and Detection Alerts. This is analysis of recorded data, not live monitoring.</p>
        <Button onClick={analyse} disabled={!modelLoaded || !ds.is_valid || busy !== null}>{busy === 'analyse' ? 'Analysing...' : 'Analyse selected dataset'}</Button>
        <hr className="my-4 border-line" />
        <h3 className="mb-1 text-[14px] font-semibold">Synthetic demonstration</h3>
        <p className="mb-2 text-[13px] text-muted">Generate benign and suspicious example flows from documented rules. This demonstrates the workflow and does not measure accuracy.</p>
        <div className="flex items-end gap-2">
          <div className="w-32"><Field label="Flows (10-5000)"><input className={inputCls} type="number" min={10} max={5000} value={synthRows} onChange={(e) => setSynthRows(Number(e.target.value))} /></Field></div>
          <Button variant="secondary" onClick={synth} disabled={!modelLoaded || busy !== null}>{busy === 'synth' ? 'Generating...' : 'Run synthetic analysis'}</Button>
        </div>
        <p className="mt-3 text-[13px]"><Link className="text-primary underline" to="/traffic">Open Traffic Analysis</Link> · <Link className="text-primary underline" to="/alerts">Open Detection Alerts</Link></p>
      </Card>
    </div>
  )
}
