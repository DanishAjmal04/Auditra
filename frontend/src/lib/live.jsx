import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import api from './api'

const LiveContext = createContext(null)
const POLL_MS = 2000
const FEED_LIMIT = 60

function beep(severity) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const tones = severity === 'CRITICAL' ? [880, 660, 880] : [740, 880]
    tones.forEach((freq, i) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.frequency.value = freq
      osc.type = 'sine'
      gain.gain.setValueAtTime(0.0001, ctx.currentTime + i * 0.16)
      gain.gain.exponentialRampToValueAtTime(0.18, ctx.currentTime + i * 0.16 + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + i * 0.16 + 0.14)
      osc.connect(gain).connect(ctx.destination)
      osc.start(ctx.currentTime + i * 0.16)
      osc.stop(ctx.currentTime + i * 0.16 + 0.15)
    })
    setTimeout(() => ctx.close(), 1200)
  } catch { /* audio blocked until the first click */ }
}

function mergeById(existing, incoming, key = 'id') {
  if (!incoming.length) return existing
  const map = new Map(existing.map((row) => [row[key], row]))
  incoming.forEach((row) => map.set(row[key], { ...map.get(row[key]), ...row, _fresh: Date.now() }))
  return Array.from(map.values())
}

export function LiveProvider({ enabled, children }) {
  const [incidents, setIncidents] = useState([])
  const [events, setEvents] = useState([])
  const [kpis, setKpis] = useState(null)
  const [agents, setAgents] = useState([])
  const [toasts, setToasts] = useState([])
  const [connected, setConnected] = useState(false)
  const [version, setVersion] = useState(0)
  const [muted, setMuted] = useState(() => {
    try { return localStorage.getItem('auditra.muted') === '1' } catch { return false }
  })
  const since = useRef(null)
  const mutedRef = useRef(muted)
  mutedRef.current = muted

  const dismiss = useCallback((id) => setToasts((all) => all.filter((t) => t.id !== id)), [])

  const toggleMute = useCallback(() => {
    setMuted((value) => {
      try { localStorage.setItem('auditra.muted', value ? '0' : '1') } catch { /* ignore */ }
      return !value
    })
  }, [])

  useEffect(() => {
    if (!enabled) return undefined
    let stopped = false
    let timer = null

    async function poll() {
      try {
        const params = since.current ? { since: since.current } : {}
        const { data } = await api.get('/live/', { params })
        if (stopped) return
        const first = since.current === null
        since.current = data.server_time
        setConnected(true)
        setKpis(data.kpis)
        setAgents(data.agents)
        if (data.incidents.length || data.events.length) setVersion((v) => v + 1)
        setIncidents((all) => mergeById(all, data.incidents)
          .sort((a, b) => new Date(b.detected_at) - new Date(a.detected_at)).slice(0, FEED_LIMIT))
        setEvents((all) => mergeById(all, data.events)
          .sort((a, b) => new Date(b.occurred_at) - new Date(a.occurred_at)).slice(0, FEED_LIMIT))
        if (!first) {
          const alerts = data.incidents.filter((i) => i.is_new && i.kind !== 'INDICATOR')
          if (alerts.length) {
            setToasts((all) => [...alerts.map((i) => ({ id: i.id, incident: i, at: Date.now() })), ...all].slice(0, 4))
            const worst = alerts.some((i) => i.severity === 'CRITICAL') ? 'CRITICAL' : alerts[0].severity
            if (!mutedRef.current && ['CRITICAL', 'HIGH'].includes(worst)) beep(worst)
          }
        }
      } catch {
        if (!stopped) setConnected(false)
      } finally {
        if (!stopped) timer = setTimeout(poll, POLL_MS)
      }
    }
    poll()
    return () => { stopped = true; clearTimeout(timer) }
  }, [enabled])

  useEffect(() => {
    if (!toasts.length) return undefined
    const timer = setInterval(() => {
      setToasts((all) => all.filter((t) => Date.now() - t.at < 12000))
    }, 1000)
    return () => clearInterval(timer)
  }, [toasts.length])

  return (
    <LiveContext.Provider value={{ incidents, events, kpis, agents, toasts, dismiss, connected, version, muted, toggleMute }}>
      {children}
    </LiveContext.Provider>
  )
}

export const useLive = () => useContext(LiveContext)
