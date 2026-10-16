import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useFetch } from '../hooks/useFetch'
import type { Overview as OverviewData } from '../types'
import { Card, EmptyState, ErrorBanner, KeyValue, LinkButton, Loading, Notice, PageHeader, Stat } from '../components/ui'
import { fmtDate, fmtInt } from '../utils/format'

export default function Overview() {
  const { data, error, loading } = useFetch<OverviewData>('/overview')
  if (loading) return <Loading />
  if (error) return <ErrorBanner message={error.message} />
  if (!data) return null

  if (!data.has_analysis || !data.latest) {
    return (
      <>
        <PageHeader title="Network Overview" subtitle="Summary of the latest traffic analysis and the state of the detection system." />
        <EmptyState
          title="No analysis available yet"
          text={data.model_loaded ? 'Import a network traffic CSV to begin.' : 'Import a network traffic CSV to begin. A model must be trained before traffic can be classified.'}
          action={<LinkButton to="/datasets">Import traffic data</LinkButton>}
        />
      </>
    )
  }

  const { analysis, class_distribution, timeline } = data.latest
  const classData = Object.entries(class_distribution).map(([name, count]) => ({ name, count }))
  return (
    <>
      <PageHeader
        title="Network Overview"
        subtitle={`Latest analysis: ${analysis.name}`}
        actions={<><LinkButton to={`/traffic?analysis=${analysis.id}`} variant="secondary">Open in Traffic Analysis</LinkButton><LinkButton to="/alerts">Review alerts</LinkButton></>}
      />
      {analysis.warnings.length > 0 && (
        <div className="mb-4 space-y-2">{analysis.warnings.map((w) => <Notice key={w} tone="warning">{w}</Notice>)}</div>
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Flows analysed" value={fmtInt(analysis.total_flows)} hint={analysis.rejected_count ? `${analysis.rejected_count} rows rejected` : undefined} />
        <Stat label="Classified normal" value={fmtInt(analysis.normal_count)} />
        <Stat label="Predicted suspicious" value={fmtInt(analysis.suspicious_count)} />
        <Stat label="High-severity alerts" value={fmtInt(analysis.high_severity_count)} hint="Severity follows the documented label policy" />
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card title="Predicted class distribution" className="xl:col-span-2">
          <div className="h-64" role="img" aria-label="Bar chart of predicted class counts">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={classData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#DCE2E8" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} allowDecimals={false} label={{ value: 'Flows', angle: -90, position: 'insideLeft', fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" name="Flows" fill="#315B78" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Detection system">
          <KeyValue rows={[
            ['Active model', data.model ? `${data.model.model_name} (${data.model.mode})` : 'None'],
            ['Model status', data.model_loaded ? 'Loaded' : 'Not loaded'],
            ['Trained on', data.model ? `${data.model.dataset_name}${data.model.is_synthetic ? ' (synthetic)' : ''}` : '-'],
            ['Evaluation', data.evaluation_available ? 'Available' : 'Unavailable'],
            ['Last analysis', fmtDate(analysis.created_at)],
            ['Open alerts', fmtInt(data.open_alerts)],
            ['Analyses stored', fmtInt(data.analyses_total)],
          ]} />
        </Card>
      </div>
      <Card title={timeline.available ? `Flows over time (${timeline.bucket_size} buckets, from flow timestamps)` : 'Flows over time'} className="mt-4">
        {timeline.available ? (
          <div className="h-64" role="img" aria-label="Stacked bar chart of normal and suspicious flows over time">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timeline.buckets.map((b) => ({ ...b, label: new Date(b.bucket).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#DCE2E8" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={24} />
                <YAxis tick={{ fontSize: 12 }} allowDecimals={false} label={{ value: 'Flows', angle: -90, position: 'insideLeft', fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="normal" name="Normal" stackId="a" fill="#28745A" isAnimationActive={false} />
                <Bar dataKey="suspicious" name="Predicted suspicious" stackId="a" fill="#A66A16" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-muted">{timeline.reason ?? 'No timestamps available.'} A time-series chart is not shown.</p>
        )}
      </Card>
    </>
  )
}
