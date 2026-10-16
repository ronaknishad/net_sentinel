import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { statusLabel } from '../utils/format'

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-[24px] font-semibold leading-tight">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-[14px] text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Card({ title, actions, children, className = '' }: { title?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-card border border-line bg-white p-4 ${className}`}>
      {(title || actions) && (
        <div className="mb-3 flex items-center justify-between gap-2">
          {title && <h2 className="text-[16px] font-semibold">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  )
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-card border border-line bg-white p-4">
      <div className="text-[12px] text-muted">{label}</div>
      <div className="mt-1 text-[24px] font-semibold leading-tight">{value}</div>
      {hint && <div className="mt-1 text-[12px] text-muted">{hint}</div>}
    </div>
  )
}

type Tone = 'normal' | 'warning' | 'critical' | 'neutral' | 'info'
const TONES: Record<Tone, string> = {
  normal: 'bg-[#E6F1EC] text-ok border-[#BFDCCF]',
  warning: 'bg-[#F7EEDD] text-warn border-[#E6CFA3]',
  critical: 'bg-[#F6E5E5] text-crit border-[#E3BEBE]',
  neutral: 'bg-badge text-muted border-line',
  info: 'bg-tint text-primary border-[#C9DAE6]',
}

export function Badge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`inline-flex items-center whitespace-nowrap rounded border px-2 py-0.5 text-[12px] font-medium ${TONES[tone]}`}>{children}</span>
}

export const ClassBadge = ({ cls, suspicious, severity }: { cls: string; suspicious: boolean; severity?: string }) => (
  <Badge tone={!suspicious ? 'normal' : severity === 'High' ? 'critical' : 'warning'}>
    {suspicious ? `Suspicious: ${cls}` : 'Normal'}
  </Badge>
)
export const SeverityBadge = ({ severity }: { severity: string }) => (
  <Badge tone={severity === 'High' ? 'critical' : severity === 'Medium' ? 'warning' : 'neutral'}>{severity}</Badge>
)
export const StatusBadge = ({ status }: { status: string }) => (
  <Badge tone={status === 'resolved' ? 'normal' : status === 'under_review' ? 'info' : 'warning'}>{statusLabel(status)}</Badge>
)

export function Button({ variant = 'primary', className = '', ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' }) {
  const base = 'inline-flex items-center gap-2 rounded-md px-3 py-2 text-[14px] font-medium disabled:cursor-not-allowed disabled:opacity-50'
  const style = variant === 'primary'
    ? 'bg-primary text-white hover:bg-primary-hover'
    : 'border border-line bg-white text-ink hover:bg-tint'
  return <button type="button" className={`${base} ${style} ${className}`} {...rest} />
}

export const LinkButton = ({ to, children, variant = 'primary' }: { to: string; children: ReactNode; variant?: 'primary' | 'secondary' }) => (
  <Link to={to} className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-[14px] font-medium ${variant === 'primary' ? 'bg-primary text-white hover:bg-primary-hover' : 'border border-line bg-white hover:bg-tint'}`}>
    {children}
  </Link>
)

export function EmptyState({ title, text, action }: { title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-line bg-white p-8 text-center">
      <h2 className="text-[16px] font-semibold">{title}</h2>
      {text && <p className="mx-auto mt-1 max-w-xl text-muted">{text}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  )
}

export function Notice({ tone = 'info', children }: { tone?: 'info' | 'warning' | 'critical' | 'normal'; children: ReactNode }) {
  const map = { info: TONES.info, warning: TONES.warning, critical: TONES.critical, normal: TONES.normal }
  return <div role={tone === 'critical' ? 'alert' : 'status'} className={`rounded-md border px-3 py-2 text-[14px] ${map[tone]}`}>{children}</div>
}

export const ErrorBanner = ({ message }: { message: string }) => <Notice tone="critical">{message}</Notice>
export const Loading = ({ label = 'Loading...' }: { label?: string }) => <p className="py-6 text-muted" role="status">{label}</p>

export function Pagination({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  return (
    <nav className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[13px] text-muted" aria-label="Pagination">
      <span>{from.toLocaleString()}-{Math.min(page * pageSize, total).toLocaleString()} of {total.toLocaleString()}</span>
      <div className="flex items-center gap-2">
        <Button variant="secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</Button>
        <span>Page {page} of {pages}</span>
        <Button variant="secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</Button>
      </div>
    </nav>
  )
}

export const th = 'whitespace-nowrap border-b border-line bg-badge px-3 py-2 text-left text-[12px] font-semibold text-muted'
export const td = 'border-b border-line px-3 py-2 text-[13px]'
export const mono = 'font-mono text-[12px]'
export const inputCls = 'w-full rounded-md border border-line bg-white px-2 py-1.5 text-[14px]'

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-[12px] text-muted">
      <span className="mb-1 block">{label}</span>
      {children}
    </label>
  )
}

export function KeyValue({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <dl className="grid grid-cols-[minmax(120px,40%)_1fr] gap-x-3 gap-y-1.5 text-[13px]">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-muted">{k}</dt>
          <dd className="break-words">{v}</dd>
        </div>
      ))}
    </dl>
  )
}

export function SidePanel({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/30" onClick={onClose}>
      <aside role="dialog" aria-label={title} className="h-full w-full max-w-md overflow-y-auto bg-white p-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-[16px] font-semibold">{title}</h2>
          <Button variant="secondary" onClick={onClose} aria-label="Close panel">Close</Button>
        </div>
        {children}
      </aside>
    </div>
  )
}
