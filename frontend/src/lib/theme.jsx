import { useCallback, useEffect, useState } from 'react'

const KEY = 'auditra.theme'

export function initialTheme() {
  try {
    return localStorage.getItem(KEY) || 'light'
  } catch {
    return 'light'
  }
}

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme
}

/** Current theme plus a toggle. Charts read colours through themeColors() so they follow the switch. */
export function useTheme() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || initialTheme())
  useEffect(() => {
    applyTheme(theme)
    try { localStorage.setItem(KEY, theme) } catch { /* private mode */ }
    window.dispatchEvent(new CustomEvent('auditra-theme', { detail: theme }))
  }, [theme])
  const toggle = useCallback(() => setTheme((t) => (t === 'dark' ? 'light' : 'dark')), [])
  return { theme, toggle }
}

export function themeColors() {
  const css = getComputedStyle(document.documentElement)
  const get = (name) => css.getPropertyValue(name).trim()
  return { grid: get('--line'), tick: get('--ink-3'), panel: get('--panel'), border: get('--line-2'), ink: get('--ink'), accent: get('--accent'), high: get('--high') }
}

export function useThemeColors() {
  const [colors, setColors] = useState(themeColors)
  useEffect(() => {
    const update = () => requestAnimationFrame(() => setColors(themeColors()))
    window.addEventListener('auditra-theme', update)
    return () => window.removeEventListener('auditra-theme', update)
  }, [])
  return colors
}
