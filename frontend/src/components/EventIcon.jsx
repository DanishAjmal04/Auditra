import {
  Ban, Bot, CalendarClock, Eraser, Eye, FilePen, FileX2, Globe, KeyRound, Lock, LogIn, Printer, ScrollText,
  ShieldAlert, ShieldOff, Timer, Unlock, Usb, UserPlus, Users,
} from 'lucide-react'

const ICONS = {
  LOGON: LogIn,
  UNLOCK: Unlock,
  LOCK: Lock,
  LOGON_FAILED: KeyRound,
  ACCOUNT_CREATED: UserPlus,
  GROUP_MEMBER_ADDED: Users,
  ACCOUNT_LOCKED: Ban,
  LOG_CLEARED: Eraser,
  AUDIT_POLICY_CHANGED: ShieldOff,
  TASK_CREATED: CalendarClock,
  FILE_READ: Eye,
  FILE_WRITE: FilePen,
  FILE_DELETE: FileX2,
  USB_CONNECTED: Usb,
  FILE_COPY_TO_USB: Usb,
  PRINT: Printer,
  WEB_VISIT: Globe,
  RETENTION_EXCEEDED: Timer,
  AUTOMATED_DECISION: Bot,
}

export default function EventIcon({ type, size = 14, className }) {
  const Icon = ICONS[type] || (type?.startsWith('FILE') ? ScrollText : ShieldAlert)
  return <Icon size={size} className={className} />
}

export function eventSentence(e) {
  // "copied salaries.csv to USB": the verb phrase without the person, used in sentences and evidence rows.
  const target = e.file_name || e.domain || e.device || e.details?.target_account || e.details?.task_name || ''
  switch (e.event_type) {
    case 'FILE_READ': return `opened ${target}`
    case 'FILE_WRITE': return `modified ${target}`
    case 'FILE_DELETE': return `deleted ${target}`
    case 'FILE_COPY_TO_USB': return `copied ${target} to USB${e.device ? ` (${e.device})` : ''}`
    case 'USB_CONNECTED': return `connected ${e.device || 'USB storage'}`
    case 'PRINT': return `printed ${target}${e.details?.printer ? ` on ${e.details.printer}` : ''}`
    case 'WEB_VISIT': return `visited ${e.domain}`
    case 'LOGON': return e.logon_type === 10 ? `remote desktop logon${e.source_ip ? ` from ${e.source_ip}` : ''}` : 'logged on'
    case 'UNLOCK': return 'unlocked the workstation'
    case 'LOCK': return 'locked the workstation'
    case 'LOGON_FAILED': return 'failed to log on'
    case 'ACCOUNT_CREATED': return `created account ${e.details?.target_account || ''}`
    case 'GROUP_MEMBER_ADDED': return `added ${e.details?.member || 'an account'} to ${e.details?.group || 'a group'}`
    case 'ACCOUNT_LOCKED': return 'account locked out by Windows'
    case 'LOG_CLEARED': return 'cleared the Security log'
    case 'AUDIT_POLICY_CHANGED': return 'changed the audit policy'
    case 'TASK_CREATED': return `created scheduled task ${e.details?.task_name || ''}`
    case 'RETENTION_EXCEEDED': return `${target} kept ${e.details?.age_days} days (limit ${e.details?.retention_days})`
    case 'AUTOMATED_DECISION': return `automated decision: ${e.details?.decision || ''}`
    default: return e.type_label || e.event_type
  }
}
