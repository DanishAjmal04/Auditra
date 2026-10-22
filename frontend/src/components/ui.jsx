import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, X } from 'lucide-react'
import { SEVERITY_STYLE, article } from '../lib/format'

export const cx = (...parts) => parts.filter(Boolean).join(' ')

export function Card({ className, children, ...props }) {
  return <div className={cx('rounded-xl border border-line bg-panel shadow-card', className)} {...props}>{children}</div>
}

export function CardHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
      <div className="min-w-0">
        <h3 className="truncate text-sm font-semibold text-ink">{title}</h3>
        {subtitle && <p className="mt-0.5 truncate text-xs text-ink-3">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-ink-3">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

const BUTTON = {
  primary: 'bg-accent text-on-accent hover:bg-accent-2 font-medium',
  secondary: 'border border-line-2 bg-panel text-ink hover:bg-panel-2',
  ghost: 'text-ink-2 hover:bg-panel-2 hover:text-ink',
  danger: 'border border-crit/30 bg-panel text-crit hover:bg-crit/5',
}

export function Button({ variant = 'secondary', size = 'md', className, loading, icon: Icon, children, ...props }) {
  const sizes = { sm: 'h-8 px-3 text-xs gap-1.5', md: 'h-9 px-3.5 text-sm gap-2' }
  return (
    <button
      className={cx('inline-flex items-center justify-center rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-50',
        BUTTON[variant], sizes[size], className)}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading ? <Loader2 size={14} className="animate-spin" /> : Icon && <Icon size={size === 'sm' ? 14 : 15} />}
      {children}
    </button>
  )
}

export function SeverityBadge({ severity, className }) {
  const s = SEVERITY_STYLE[severity] || SEVERITY_STYLE.LOW
  return (
    <span className={cx('inline-flex items-center gap-1.5 text-[11px] font-semibold tracking-wide', s.text, className)}>
      <span className={cx('h-2 w-2 rounded-full', s.dot)} />
      {severity}
    </span>
  )
}

export function Pill({ children, tone = 'default', className }) {
  const tones = {
    default: 'bg-panel-2 text-ink-2',
    accent: 'bg-accent/8 text-accent',
    ok: 'bg-ok/10 text-ok',
    warn: 'bg-med/10 text-med',
    crit: 'bg-crit/8 text-crit',
  }
  return (
    <span className={cx('inline-flex items-center gap-1 whitespace-nowrap rounded-md px-1.5 py-0.5 text-[11px] font-medium', tones[tone], className)}>
      {children}
    </span>
  )
}

export function Articles({ items = [], max = 4 }) {
  const shown = items.slice(0, max).map(article)
  return (
    <span className="text-xs font-medium text-ink-2">
      {shown.join(' · ')}{items.length > max && ` +${items.length - max}`}
    </span>
  )
}

export function ScoreBar({ score, severity, wide }) {
  const s = SEVERITY_STYLE[severity] || SEVERITY_STYLE.LOW
  return (
    <div className={cx('flex items-center gap-2', wide ? 'w-full' : 'w-28')}>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
        <div className={cx('h-full rounded-full', s.bar)} style={{ width: `${Math.max(3, score)}%` }} />
      </div>
      <span className={cx('tabular w-7 text-right text-xs font-semibold', s.text)}>{score}</span>
    </div>
  )
}

export function Stat({ label, value, hint, tone, to }) {
  const tones = { crit: 'text-crit', high: 'text-high', ok: 'text-ok', accent: 'text-accent' }
  const body = (
    <Card className={cx('px-5 py-4', to && 'transition-colors hover:border-accent/40')}>
      <p className="text-xs font-medium text-ink-3">{label}</p>
      <p className={cx('tabular mt-2 text-[28px] font-semibold leading-none tracking-tight', tones[tone] || 'text-ink')}>{value ?? '—'}</p>
      {hint && <p className="mt-2 truncate text-xs text-ink-3">{hint}</p>}
    </Card>
  )
  return to ? <Link to={to} className="block">{body}</Link> : body
}

export function Empty({ icon: Icon, title, children }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      {Icon && <Icon size={22} className="mb-3 text-ink-3" />}
      <p className="text-sm font-medium text-ink-2">{title}</p>
      {children && <div className="mt-1 max-w-md text-xs text-ink-3">{children}</div>}
    </div>
  )
}

export function Spinner({ label = 'Loading' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-ink-3">
      <Loader2 size={16} className="animate-spin" /> {label}
    </div>
  )
}

export function ErrorNote({ children }) {
  if (!children) return null
  return <div className="rounded-lg border border-crit/30 bg-crit/10 px-3 py-2 text-sm text-crit">{children}</div>
}

export function Field({ label, hint, children, className }) {
  return (
    <label className={cx('block', className)}>
      <span className="mb-1.5 block text-xs font-medium text-ink-2">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-ink-3">{hint}</span>}
    </label>
  )
}

const INPUT = 'h-9 w-full rounded-lg border border-line-2 bg-canvas px-3 text-sm text-ink placeholder:text-ink-3 outline-none focus:border-accent focus:ring-2 focus:ring-accent/20'

export function Input({ className, ...props }) {
  return <input className={cx(INPUT, className)} {...props} />
}

export function Textarea({ className, ...props }) {
  return <textarea className={cx(INPUT, 'h-auto min-h-20 py-2', className)} {...props} />
}

export function Select({ className, options, placeholder, ...props }) {
  const entries = Array.isArray(options) ? options.map((o) => (Array.isArray(o) ? o : [o, o])) : Object.entries(options)
  return (
    <select className={cx(INPUT, 'pr-8', className)} {...props}>
      {placeholder !== undefined && <option value="">{placeholder}</option>}
      {entries.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
    </select>
  )
}

export function Checkbox({ label, className, ...props }) {
  return (
    <label className={cx('flex cursor-pointer items-center gap-2 text-sm text-ink-2', className)}>
      <input type="checkbox" className="h-4 w-4 rounded border-line-2 bg-canvas accent-sky-400" {...props} />
      {label}
    </label>
  )
}

export function Modal({ open, onClose, title, subtitle, children, footer, width = 'max-w-lg' }) {
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/45 p-4 pt-[8vh] backdrop-blur-sm" onMouseDown={onClose}>
      <div className={cx('slide-in w-full rounded-xl border border-line-2 bg-panel shadow-2xl', width)} onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div>
            <h2 className="text-base font-semibold">{title}</h2>
            {subtitle && <p className="mt-0.5 text-xs text-ink-3">{subtitle}</p>}
          </div>
          <button onClick={onClose} className="rounded-md p-1 text-ink-3 hover:bg-panel-2 hover:text-ink"><X size={16} /></button>
        </div>
        <div className="max-h-[65vh] overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-line px-5 py-3">{footer}</div>}
      </div>
    </div>
  )
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="mb-4 flex gap-1 overflow-x-auto border-b border-line">
      {tabs.map(([key, label, count]) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={cx('-mb-px flex items-center gap-2 whitespace-nowrap border-b-2 px-3 py-2 text-sm transition-colors',
            value === key ? 'border-accent text-ink' : 'border-transparent text-ink-3 hover:text-ink-2')}
        >
          {label}
          {count !== undefined && <span className="tabular rounded bg-panel-2 px-1.5 text-[11px] text-ink-3">{count}</span>}
        </button>
      ))}
    </div>
  )
}

export function Table({ columns, rows, onRowClick, empty, rowKey = 'id', rowClass }) {
  if (!rows?.length) return empty || null
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-line text-[11px] font-medium uppercase tracking-wider text-ink-3">
            {columns.map((c) => <th key={c.key} className={cx('px-5 py-3 font-medium', c.className)}>{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row[rowKey]}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cx('border-b border-line/70 last:border-0', onRowClick && 'cursor-pointer hover:bg-panel-2/60', rowClass?.(row))}
            >
              {columns.map((c) => <td key={c.key} className={cx('px-5 py-3 align-middle', c.className)}>{c.render ? c.render(row) : row[c.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
