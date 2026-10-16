import type { ReactNode } from 'react'
import { useFetch } from '../hooks/useFetch'
import type { SystemInfo } from '../types'
import { Badge, Card, ErrorBanner, KeyValue, Loading, mono, Notice, PageHeader, td, th } from '../components/ui'
import { fmtBytes, fmtDate } from '../utils/format'

export default function SettingsPage() {
  const { data, error, loading } = useFetch<SystemInfo>('/system/info')
  if (loading) return <Loading />
  if (error) return <ErrorBanner message={error.message} />
  if (!data) return null
  const md = data.model.metadata
  return (
    <>
      <PageHeader title="System Status" subtitle="Backend, model and storage information reported by the running application." />
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Application">
          <KeyValue rows={[
            ['Name', data.app.name], ['Version', data.app.version],
            ['Backend health', <Badge tone="normal">Reachable</Badge>],
            ['Live traffic capture', <Badge tone="neutral">Not configured</Badge>],
          ]} />
          <div className="mt-3"><Notice>{data.live_capture.message} This version analyses recorded flow datasets only.</Notice></div>
        </Card>
        <Card title="Model">
          <KeyValue rows={[
            ['Status', <Badge tone={data.model.loaded ? 'normal' : 'warning'}>{data.model.loaded ? 'Loaded' : 'Not loaded'}</Badge>],
            ['Message', data.model.message],
            ['Evaluation report', data.model.evaluation_available ? 'Available' : 'Unavailable'],
            ...(md ? ([
              ['Model', `${md.model_name} (${md.mode})`], ['Model ID', <span className={mono}>{md.model_id}</span>],
              ['Trained on', `${md.dataset_name}${md.is_synthetic ? ' (synthetic)' : ''}`], ['Trained', fmtDate(md.trained_at)],
              ['Classes', md.classes.join(', ')], ['Input features', String(md.feature_names.length)],
            ] as [string, ReactNode][]) : []),
          ]} />
        </Card>
        <Card title="Local storage">
          <KeyValue rows={[
            ['Dataset directory', <span className={mono}>{data.datasets.directory}</span>],
            ['Stored datasets', `${data.datasets.file_count} files, ${fmtBytes(data.datasets.total_bytes)}`],
            ['Database', <span className={mono}>{data.storage.database_path}</span>],
            ['Database status', data.storage.database_exists ? `Present, ${fmtBytes(data.storage.database_bytes)}` : 'Not created yet'],
          ]} />
        </Card>
        <Card title="Severity policy">
          <p className="mb-2 text-[13px] text-muted">Severity is assigned from the predicted label only. It is not derived from model confidence.</p>
          <table className="w-full border-collapse"><thead><tr><th className={th}>Severity</th><th className={th}>Rule</th></tr></thead>
            <tbody>{data.severity_policy.map((s) => <tr key={s.severity}><td className={td}>{s.severity}</td><td className={td}>{s.rule}</td></tr>)}</tbody></table>
        </Card>
      </div>
      <Card title={`Supported input schema (version ${data.input_schema.version})`} className="mt-4">
        <p className="mb-2 text-[13px] text-muted">Datasets are mapped to these features automatically using the accepted headers. IP addresses, flow IDs, timestamps and source ports are never used as model input.</p>
        <div className="overflow-x-auto"><table className="w-full border-collapse">
          <thead><tr>{['Feature', 'Description', 'Accepted headers'].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
          <tbody>{data.input_schema.features.map((f) => (
            <tr key={f.name}><td className={`${td} ${mono}`}>{f.name}</td><td className={td}>{f.description}</td><td className={`${td} ${mono}`}>{f.accepted_headers.join(', ') || f.name}</td></tr>
          ))}</tbody>
        </table></div>
      </Card>
    </>
  )
}
