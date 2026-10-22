import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  Activity, BellOff, BellRing, Database, FileText, FolderLock, Gauge, LogOut, Monitor, Moon, ScrollText, ShieldAlert,
  ShieldCheck, SlidersHorizontal, Sun, UserCog, Users,
} from 'lucide-react'
import { useAuth } from '../lib/auth'
import { useLive } from '../lib/live'
import { useTheme } from '../lib/theme'
import { cx } from './ui'
import Toasts from './Toasts'

const OFFICER = [
  ['/', 'Overview', Gauge],
  ['/incidents', 'Incidents', ShieldAlert],
  ['/employees', 'Employees', Users],
  ['/activity', 'Activity', Activity],
  ['/records', 'GDPR Records', Database],
  ['/reports', 'Reports', FileText],
]

const ADMIN = [
  ['/admin/employees', 'Employees & Access', UserCog],
  ['/admin/catalogue', 'Data Catalogue', FolderLock],
  ['/admin/rules', 'Detection Rules', SlidersHorizontal],
  ['/admin/agents', 'Agents & Health', Monitor],
  ['/admin/users', 'Console Users', ShieldCheck],
  ['/admin/audit', 'Audit Trail', ScrollText],
]

function NavItem({ to, label, icon: Icon, badge }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) => cx('group relative flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm transition-colors',
        isActive
          ? 'bg-side-2 font-medium text-side-ink before:absolute before:-left-2.5 before:bottom-1.5 before:top-1.5 before:w-0.5 before:rounded-full before:bg-side-accent'
          : 'text-side-ink-2 hover:bg-side-2 hover:text-side-ink')}
    >
      <Icon size={16} className="shrink-0" />
      <span className="flex-1 truncate">{label}</span>
      {badge ? <span className="tabular rounded-md bg-crit px-1.5 text-[11px] font-semibold text-white">{badge}</span> : null}
    </NavLink>
  )
}

export default function Layout() {
  const { user, logout, isAdmin } = useAuth()
  const { kpis, connected, agents, muted, toggleMute } = useLive()
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()
  const online = agents.filter((a) => a.online).length

  return (
    <div className="flex h-full">
      <aside className="flex w-60 shrink-0 flex-col border-r border-side-line bg-side text-side-ink">
        <div className="flex items-center gap-2.5 px-4 py-4">
          <img src="/favicon.svg" alt="" className="h-8 w-8" />
          <div>
            <p className="text-sm font-semibold tracking-tight text-side-ink">Auditra</p>
            <p className="text-[11px] text-side-ink-2">GDPR compliance console</p>
          </div>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2.5 pb-4">
          <p className="px-2.5 pb-1.5 pt-2 text-[10px] font-semibold uppercase tracking-widest text-side-ink-2">Monitoring</p>
          {OFFICER.map(([to, label, icon]) => (
            <NavItem key={to} to={to} label={label} icon={icon}
              badge={to === '/incidents' ? kpis?.critical_open + kpis?.high_open || null : null} />
          ))}
          {isAdmin && (
            <>
              <p className="px-2.5 pb-1.5 pt-5 text-[10px] font-semibold uppercase tracking-widest text-side-ink-2">Administration</p>
              {ADMIN.map(([to, label, icon]) => <NavItem key={to} to={to} label={label} icon={icon} />)}
            </>
          )}
        </nav>
        <div className="border-t border-side-line p-3">
          <div className="mb-3 space-y-1.5 rounded-lg border border-side-line bg-side-2 px-3 py-2 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-side-ink-2">Live feed</span>
              <span className={cx('flex items-center gap-1.5 font-medium', connected ? 'text-emerald-400' : 'text-red-400')}>
                <span className={cx('h-1.5 w-1.5 rounded-full', connected ? 'pulse-dot bg-emerald-400' : 'bg-red-400')} />
                {connected ? 'connected' : 'offline'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-side-ink-2">Agents online</span>
              <span className={cx('tabular font-medium', online ? 'text-emerald-400' : 'text-side-ink-2')}>{online} / {agents.length}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-side-2 text-xs font-semibold uppercase text-side-ink">
              {(user?.name || user?.username || '?').slice(0, 2)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-side-ink">{user?.name}</p>
              <p className="truncate text-[11px] text-side-ink-2">{isAdmin ? 'Administrator' : 'Compliance officer'}</p>
            </div>
            <button title={theme === 'dark' ? 'Light mode' : 'Dark mode'} onClick={toggle}
              className="rounded-md p-1.5 text-side-ink-2 hover:bg-side-2 hover:text-side-ink">
              {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
            </button>
            <button title={muted ? 'Unmute alerts' : 'Mute alerts'} onClick={toggleMute}
              className="rounded-md p-1.5 text-side-ink-2 hover:bg-side-2 hover:text-side-ink">
              {muted ? <BellOff size={15} /> : <BellRing size={15} />}
            </button>
            <button title="Sign out" onClick={async () => { await logout(); navigate('/login') }}
              className="rounded-md p-1.5 text-side-ink-2 hover:bg-side-2 hover:text-side-ink">
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>
      <main className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-[1440px] px-6 py-6">
          <Outlet />
        </div>
      </main>
      <Toasts />
    </div>
  )
}
