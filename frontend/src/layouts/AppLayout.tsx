import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Activity, BarChart3, Database, LayoutDashboard, Menu, Settings, ShieldAlert, X } from 'lucide-react'
import { api, MODEL_CHANGED } from '../services/api'
import type { ModelStatus } from '../types'

const NAV = [
  { to: '/', label: 'Network Overview', icon: LayoutDashboard, end: true },
  { to: '/traffic', label: 'Traffic Analysis', icon: Activity },
  { to: '/alerts', label: 'Detection Alerts', icon: ShieldAlert },
  { to: '/evaluation', label: 'Model Evaluation', icon: BarChart3 },
  { to: '/datasets', label: 'Dataset Management', icon: Database },
  { to: '/settings', label: 'System Status', icon: Settings },
]

export default function AppLayout() {
  const [open, setOpen] = useState(false)
  const [model, setModel] = useState<ModelStatus | null>(null)
  const [backendUp, setBackendUp] = useState<boolean | null>(null)
  const location = useLocation()

  useEffect(() => {
    const load = () =>
      api.get<ModelStatus>('/model/status').then((m) => { setModel(m); setBackendUp(true) }).catch(() => setBackendUp(false))
    load()
    window.addEventListener(MODEL_CHANGED, load)
    return () => window.removeEventListener(MODEL_CHANGED, load)
  }, [])
  useEffect(() => setOpen(false), [location.pathname])

  const nav = (
    <nav aria-label="Main navigation" className="mt-4 flex flex-col gap-1 px-3">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink key={to} to={to} end={end}
          className={({ isActive }) => `flex items-center gap-3 rounded-md px-3 py-2 text-[14px] ${isActive ? 'bg-primary text-white' : 'text-[#C5D0DA] hover:bg-white/10'}`}>
          <Icon size={18} aria-hidden="true" />
          {label}
        </NavLink>
      ))}
    </nav>
  )

  const brand = (
    <div className="px-6 pt-5">
      <div className="text-[18px] font-semibold text-white">NetSentinel</div>
      <div className="mt-0.5 text-[12px] text-[#9FB0BF]">Intrusion detection prototype</div>
    </div>
  )

  return (
    <div className="flex min-h-full">
      <aside className="hidden w-60 shrink-0 bg-sidebar lg:block">{brand}{nav}</aside>
      {open && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <aside className="w-60 bg-sidebar">{brand}{nav}</aside>
          <button className="flex-1 bg-black/40" aria-label="Close navigation" onClick={() => setOpen(false)} />
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-line bg-white px-4 py-3">
          <div className="flex items-center gap-3">
            <button className="rounded-md border border-line p-2 lg:hidden" aria-label={open ? 'Close navigation' : 'Open navigation'} onClick={() => setOpen(!open)}>
              {open ? <X size={18} /> : <Menu size={18} />}
            </button>
            <span className="text-[13px] text-muted">Simulated 5G/IoT traffic analysis. Recorded datasets only; live capture is not configured.</span>
          </div>
          <div className="flex shrink-0 items-center gap-2 text-[13px]" aria-live="polite">
            {backendUp === false ? (
              <span className="rounded border border-[#E3BEBE] bg-[#F6E5E5] px-2 py-1 text-crit">Backend unreachable</span>
            ) : model?.loaded ? (
              <span className="rounded border border-[#BFDCCF] bg-[#E6F1EC] px-2 py-1 text-ok">
                Model loaded: {model.metadata?.model_name} ({model.metadata?.mode})
              </span>
            ) : (
              <span className="rounded border border-[#E6CFA3] bg-[#F7EEDD] px-2 py-1 text-warn">No model loaded</span>
            )}
          </div>
        </header>
        <main className="min-w-0 flex-1 p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
