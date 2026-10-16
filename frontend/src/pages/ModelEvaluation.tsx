import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Download } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useFetch } from '../hooks/useFetch'
import type { Evaluation } from '../types'
import { Card, EmptyState, ErrorBanner, Field, inputCls, KeyValue, Loading, LinkButton, mono, Notice, PageHeader, Stat, td, th } from '../components/ui'
import { featureLabel, fmtDate, fmtInt, fmtPct, fmtScore } from '../utils/format'

const METRIC_HELP: [string, string][] = [
  ['Accuracy', 'Share of all test flows classified correctly. Misleading when one class dominates.'],
  ['Precision', 'Of the flows flagged as a class, the share that truly belonged to it. Low precision means false alarms.'],
  ['Recall', 'Of the flows that truly belonged to a class, the share the model found. Low recall means missed attacks.'],
  ['F1-score', 'Harmonic mean of precision and recall. Useful when both error types matter.'],
  ['Normal flows flagged', 'Share of normal test flows predicted as suspicious. This is the false positive rate that costs analyst time.'],
]

function Heatmap({ labels, matrix }: { labels: string[]; matrix: number[][] }) {
  const max = Math.max(1, ...matrix.flat())
  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-[13px]" aria-label="Confusion matrix: rows are actual classes, columns are predicted classes">
        <thead><tr><th className={th}>Actual \ Predicted</th>{labels.map((l) => <th key={l} className={th}>{l}</th>)}</tr></thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={labels[i]}>
              <th scope="row" className={`${th} bg-white`}>{labels[i]}</th>
              {row.map((v, j) => (
                <td key={j} className={`${td} text-center ${mono}`}
                  style={{ background: `rgba(49,91,120,${(v / max) * 0.85})`, color: v / max > 0.45 ? '#fff' : '#202B36', outline: i === j ? '2px solid #315B78' : undefined, outlineOffset: -2 }}>
                  {fmtInt(v)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-[12px] text-muted">Outlined cells on the diagonal are correct predictions. Cell shading is proportional to count.</p>
    </div>
  )
}

export default function ModelEvaluation() {
  const { data, error, loading } = useFetch<Evaluation>('/models/evaluation')
  const [modelName, setModelName] = useState<string | null>(null)

  if (loading) return <Loading />
  if (error?.status === 404) {
    return (<>
      <PageHeader title="Model Evaluation" />
      <EmptyState title="Model evaluation is unavailable" text="Train or load a model first. Metrics appear here only after training and evaluation have completed." action={<LinkButton to="/datasets">Go to Dataset Management</LinkButton>} />
    </>)
  }
  if (error) return <ErrorBanner message={error.message} />
  if (!data) return null

  const name = modelName ?? data.selected_model
  const m = data.models[name]
  const classData = data.classes.map((c) => ({ name: c, count: data.class_distribution[c] ?? 0 }))
  const perClass = m.per_class.map((c) => ({ name: c.class, Precision: +c.precision.toFixed(3), Recall: +c.recall.toFixed(3), F1: +c.f1.toFixed(3) }))
  const comparison = data.model_comparison.map((r) => ({ name: r.model, Precision: +r.precision.toFixed(3), Recall: +r.recall.toFixed(3), F1: +r.f1.toFixed(3) }))
  const dl = 'inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-[14px] font-medium hover:bg-tint'

  return (
    <>
      <PageHeader title="Model Evaluation" subtitle="Metrics computed from predictions on a held-out test split. Nothing here is estimated."
        actions={<>
          <a className={dl} href="/api/exports/evaluation?format=csv"><Download size={16} aria-hidden="true" /> CSV report</a>
          <a className={dl} href="/api/exports/evaluation?format=json"><Download size={16} aria-hidden="true" /> JSON report</a>
        </>} />
      <div className="mb-4"><Notice tone={data.is_synthetic ? 'warning' : 'info'}>{data.provenance_note}</Notice></div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Accuracy" value={fmtPct(m.accuracy)} />
        <Stat label="Precision" value={fmtPct(m.headline.precision)} hint={m.averaging} />
        <Stat label="Recall" value={fmtPct(m.headline.recall)} />
        <Stat label="F1-score" value={fmtPct(m.headline.f1)} />
        <Stat label="Normal flows flagged" value={fmtPct(m.normal_flagged_rate, 2)} hint="False positive rate" />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card title="Run details">
          <KeyValue rows={[
            ['Selected model', data.selected_model],
            ['Model ID', <span className={mono}>{data.model_id}</span>],
            ['Mode', data.mode],
            ['Dataset', data.dataset_name],
            ['Trained', fmtDate(data.trained_at)],
            ['Train / test samples', `${fmtInt(data.split.train_samples)} / ${fmtInt(data.split.test_samples)}`],
            ['Split', `${Math.round((1 - data.split.test_size) * 100)}% / ${Math.round(data.split.test_size * 100)}%, stratified, seed ${data.random_seed}`],
            ['Rows before / after cleaning', `${fmtInt(data.preprocessing.rows_before)} / ${fmtInt(data.preprocessing.rows_after)}`],
            ['Duplicates removed', fmtInt(data.preprocessing.dropped_duplicates)],
            ['Training time', `${m.training_seconds}s (${name})`],
            ...(Object.keys(data.dropped_classes).length ? [['Classes excluded (too few samples)', Object.entries(data.dropped_classes).map(([k, v]) => `${k} (${v})`).join(', ')] as [string, string]] : []),
          ]} />
        </Card>
        <Card title="Class distribution (after cleaning)" className="xl:col-span-2">
          <div className="h-56" role="img" aria-label="Bar chart of class distribution">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={classData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#DCE2E8" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} label={{ value: 'Flows', angle: -90, position: 'insideLeft', fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" name="Flows" fill="#315B78" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          {Math.min(...classData.map((c) => c.count)) < 0.05 * classData.reduce((s, c) => s + c.count, 0) && (
            <p className="mt-2 text-[13px] text-muted">Classes are imbalanced, so accuracy alone can be misleading. Compare recall and the false positive rate.</p>
          )}
        </Card>
      </div>

      <Card title="Model comparison" className="mt-4">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead><tr>{['Model', 'Accuracy', 'Precision', 'Recall', 'F1', 'Normal flagged', 'Training (s)'].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
            <tbody>
              {data.model_comparison.map((r) => (
                <tr key={r.model} className={r.model === data.selected_model ? 'bg-tint' : ''}>
                  <td className={td}>{r.model}{r.model === data.selected_model ? ' (selected)' : ''}</td>
                  <td className={`${td} ${mono}`}>{fmtScore(r.accuracy)}</td><td className={`${td} ${mono}`}>{fmtScore(r.precision)}</td>
                  <td className={`${td} ${mono}`}>{fmtScore(r.recall)}</td><td className={`${td} ${mono}`}>{fmtScore(r.f1)}</td>
                  <td className={`${td} ${mono}`}>{fmtPct(r.normal_flagged_rate, 2)}</td><td className={`${td} ${mono}`}>{r.training_seconds}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 h-56" role="img" aria-label="Grouped bar chart comparing precision, recall and F1 across models">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={comparison}>
              <CartesianGrid strokeDasharray="3 3" stroke="#DCE2E8" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} /><YAxis domain={[0, 1]} tick={{ fontSize: 12 }} /><Tooltip /><Legend />
              <Bar dataKey="Precision" fill="#315B78" isAnimationActive={false} />
              <Bar dataKey="Recall" fill="#28745A" isAnimationActive={false} />
              <Bar dataKey="F1" fill="#8A97A5" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card title="Per-model detail" className="mt-4" actions={
        <Field label="Model"><select className={inputCls} value={name} onChange={(e) => setModelName(e.target.value)}>
          {Object.keys(data.models).map((k) => <option key={k}>{k}</option>)}
        </select></Field>}>
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <div><h3 className="mb-2 text-[14px] font-semibold">Confusion matrix</h3><Heatmap labels={m.confusion_matrix.labels} matrix={m.confusion_matrix.matrix} /></div>
          <div>
            <h3 className="mb-2 text-[14px] font-semibold">Per-class metrics</h3>
            <div className="overflow-x-auto"><table className="w-full border-collapse">
              <thead><tr>{['Class', 'Precision', 'Recall', 'F1', 'Support', 'FPR (one-vs-rest)'].map((h) => <th key={h} className={th}>{h}</th>)}</tr></thead>
              <tbody>{m.per_class.map((c) => (
                <tr key={c.class}><td className={td}>{c.class}</td><td className={`${td} ${mono}`}>{fmtScore(c.precision)}</td><td className={`${td} ${mono}`}>{fmtScore(c.recall)}</td>
                  <td className={`${td} ${mono}`}>{fmtScore(c.f1)}</td><td className={`${td} ${mono}`}>{fmtInt(c.support)}</td><td className={`${td} ${mono}`}>{fmtPct(c.false_positive_rate, 2)}</td></tr>
              ))}</tbody>
            </table></div>
            <div className="mt-3 h-52" role="img" aria-label="Grouped bar chart of per-class precision, recall and F1">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={perClass}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#DCE2E8" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} /><YAxis domain={[0, 1]} tick={{ fontSize: 12 }} /><Tooltip /><Legend />
                  <Bar dataKey="Precision" fill="#315B78" isAnimationActive={false} />
                  <Bar dataKey="Recall" fill="#28745A" isAnimationActive={false} />
                  <Bar dataKey="F1" fill="#8A97A5" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </Card>

      {data.feature_importances && (
        <Card title={`Feature importance (${data.selected_model}, top 10)`} className="mt-4">
          <div className="h-64" role="img" aria-label="Horizontal bar chart of feature importances">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart layout="vertical" data={data.feature_importances.slice(0, 10).map((f) => ({ name: featureLabel(f.feature), value: +f.importance.toFixed(4) }))} margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#DCE2E8" />
                <XAxis type="number" tick={{ fontSize: 12 }} /><YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 12 }} /><Tooltip />
                <Bar dataKey="value" name="Importance" fill="#315B78" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      <Card title="What the metrics mean" className="mt-4">
        <dl className="space-y-2 text-[13px]">{METRIC_HELP.map(([k, v]) => <div key={k}><dt className="inline font-semibold">{k}: </dt><dd className="inline text-muted">{v}</dd></div>)}</dl>
        <p className="mt-3 text-[13px] text-muted">In intrusion detection, missed attacks (low recall) and false alarms (high false positive rate) both have operational cost. {data.probability_note}</p>
        <p className="mt-2 text-[13px]"><Link className="text-primary underline" to="/datasets">Train another model</Link></p>
      </Card>
    </>
  )
}
