export const SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

export const SEVERITY_STYLE = {
  CRITICAL: { text: 'text-crit', bg: 'bg-crit/12', ring: 'ring-crit/30', bar: 'bg-crit', dot: 'bg-crit' },
  HIGH: { text: 'text-high', bg: 'bg-high/12', ring: 'ring-high/30', bar: 'bg-high', dot: 'bg-high' },
  MEDIUM: { text: 'text-med', bg: 'bg-med/12', ring: 'ring-med/30', bar: 'bg-med', dot: 'bg-med' },
  LOW: { text: 'text-ink-2', bg: 'bg-low/15', ring: 'ring-low/30', bar: 'bg-low', dot: 'bg-low' },
}

export const SEVERITY_HEX = { CRITICAL: '#dc2626', HIGH: '#ea580c', MEDIUM: '#d97706', LOW: '#94a3b8' }

export const CATEGORIES = {
  GENERAL: 'General business',
  FINANCIAL: 'Financial',
  HR_EMPLOYEE: 'HR / employee records',
  HEALTH: 'Health (special category)',
  BIOMETRIC: 'Biometric (special category)',
  CRIMINAL: 'Criminal offence data',
  NATIONAL_ID: 'National ID (CNIC)',
  CUSTOMER: 'Customer personal data',
}

export const EMPLOYEE_ROLES = {
  INTERN: 'Intern', STAFF: 'Staff', ANALYST: 'Analyst', MANAGER: 'Manager', HR_OFFICER: 'HR officer',
  MEDICAL_OFFICER: 'Medical officer', IT_ADMIN: 'IT administrator', CONTRACTOR: 'Contractor',
}

export const LAWFUL_BASES = {
  CONSENT: 'Consent', CONTRACT: 'Contract', LEGAL_OBLIGATION: 'Legal obligation', VITAL_INTEREST: 'Vital interest',
  PUBLIC_TASK: 'Public task', LEGITIMATE_INTEREST: 'Legitimate interest',
}

export const STATUS_LABEL = {
  OPEN: 'Open', ACKNOWLEDGED: 'Acknowledged', INVESTIGATING: 'Investigating', ESCALATED: 'Escalated to DPO',
  RESOLVED: 'Resolved', FALSE_POSITIVE: 'False positive',
}

export const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export function article(a) {
  return a === 'Policy' ? 'Policy' : a === 'AI' ? 'AI' : `Art. ${a}`
}

const timeFmt = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' })
const dayFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' })
const fullFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })

export function time(value) {
  return value ? timeFmt.format(new Date(value)) : '—'
}

export function dayTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  const today = new Date()
  return d.toDateString() === today.toDateString() ? timeFmt.format(d) : `${dayFmt.format(d)} ${timeFmt.format(d)}`
}

export function full(value) {
  return value ? fullFmt.format(new Date(value)) : '—'
}

export function ago(value) {
  if (!value) return 'never'
  const seconds = Math.round((Date.now() - new Date(value).getTime()) / 1000)
  if (seconds < 5) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}

export function who(row) {
  return row?.employee?.full_name || row?.account || 'Organisation'
}

export function shortPath(path) {
  if (!path) return ''
  const parts = path.split('\\')
  return parts.length > 3 ? `…\\${parts.slice(-2).join('\\')}` : path
}
