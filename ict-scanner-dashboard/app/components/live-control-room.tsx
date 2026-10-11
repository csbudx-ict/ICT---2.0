'use client'

import { useEffect, useRef, useState } from 'react'
import {
  Activity,
  Check,
  ChevronRight,
  Clock3,
  Menu,
  Play,
  Radio,
  RefreshCw,
  Settings2,
  ShieldCheck,
  X,
} from 'lucide-react'

const MODULES = [
  { id: 'unicorn_setup', label: 'Unicorn Setup', detail: 'Breaker + FVG with MSS displacement' },
  { id: 'silver_bullet_fvg', label: 'Silver Bullet / FVG', detail: 'Three-candle imbalance and 50% retracement' },
  { id: 'institutional_order_block', label: 'Institutional Order Block', detail: 'Displacement break and 50% mean threshold' },
  { id: 'breaker_blocks', label: 'Breaker Blocks', detail: 'Invalidated order blocks' },
  { id: 'premium_discount', label: 'Premium & Discount Zones', detail: 'Dealing-range equilibrium split' },
  { id: 'box_liquidity', label: 'BOX / Liquidity Models', detail: 'Consolidation, liquidity pools, and sweeps' },
  { id: 'master_sniper', label: 'Master Sniper Confluence', detail: 'Full confluence entry gate' },
  { id: 'fvg', label: 'Fair Value Gaps', detail: 'Unmitigated three-candle gaps' },
  { id: 'order_blocks', label: 'Order Blocks', detail: 'Last opposing candle before displacement' },
  { id: 'ote_fibonacci', label: 'OTE Fibonacci', detail: '0.618–0.790 zone with 0.705 sweet spot' },
] as const

type ModuleKey = (typeof MODULES)[number]['id']
type ModuleSelection = Record<ModuleKey, boolean>
type ModuleSignal = Record<string, unknown>
type PairSnapshot = {
  symbol: string
  provider: string
  status: 'CONNECTED' | 'UNAVAILABLE'
  timestamp?: string
  error?: string
  candle?: { open: number; high: number; low: number; close: number }
  modules?: Record<ModuleKey, { enabled: boolean; signal: ModuleSignal | null }>
  advanced_ict?: Record<string, unknown> | null
}
type DetectedEntry = {
  id: string
  symbol: string
  module: string
  module_label: string
  direction: 'BUY' | 'SELL'
  timestamp: string
  entry: number | null
  low: number | null
  high: number | null
  mean_threshold: number | null
  displacement_atr: number | null
  rank: number
  rank_score: number
  provider: string
}
type DashboardMessage = {
  type: 'dashboard'
  generated_at: string
  scan_interval_seconds: number
  pairs: PairSnapshot[]
  entries?: DetectedEntry[]
}
type SocketStatus = 'connecting' | 'connected' | 'reconnecting'

const HEARTBEAT_INTERVAL_MS = 15_000
const HEARTBEAT_TIMEOUT_MS = 45_000

const DEFAULT_SELECTION = Object.fromEntries(
  MODULES.map(({ id }) => [id, true]),
) as ModuleSelection

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isDetectedEntry(value: unknown): value is DetectedEntry {
  return isRecord(value) &&
    typeof value.id === 'string' &&
    typeof value.symbol === 'string' &&
    typeof value.module === 'string' &&
    typeof value.module_label === 'string' &&
    (value.direction === 'BUY' || value.direction === 'SELL') &&
    typeof value.timestamp === 'string' &&
    typeof value.rank === 'number' &&
    typeof value.rank_score === 'number' &&
    typeof value.provider === 'string' &&
    ['entry', 'low', 'high', 'mean_threshold', 'displacement_atr'].every(
      (key) => value[key] === null || typeof value[key] === 'number',
    )
}

function isDashboardMessage(value: unknown): value is DashboardMessage {
  if (!isRecord(value) || value.type !== 'dashboard' || !Array.isArray(value.pairs)) return false
  return value.pairs.every(
    (pair) =>
      isRecord(pair) &&
      typeof pair.symbol === 'string' &&
      typeof pair.provider === 'string' &&
      (pair.status === 'CONNECTED' || pair.status === 'UNAVAILABLE'),
  )
}

function signalLines(signal: ModuleSignal) {
  return Object.entries(signal)
    .filter(([, value]) => ['string', 'number', 'boolean'].includes(typeof value))
    .map(([key, value]) =>
      typeof value === 'number'
        ? `${key.replaceAll('_', ' ')}: ${value.toFixed(5)}`
        : `${key.replaceAll('_', ' ')}: ${String(value)}`,
    )
}

function formatPrice(value: number | null | undefined) {
  return value == null ? '—' : value.toPrecision(7)
}

function advancedSignalLines(signal: unknown): string[] {
  if (!isRecord(signal)) return []
  return Object.entries(signal)
    .filter(([, value]) => ['string', 'number', 'boolean'].includes(typeof value))
    .map(([key, value]) =>
      typeof value === 'number'
        ? `${key.replaceAll('_', ' ')}: ${value.toPrecision(5)}`
        : `${key.replaceAll('_', ' ')}: ${String(value)}`,
    )
}

export default function LiveControlRoom() {
  const [selection, setSelection] = useState<ModuleSelection>(DEFAULT_SELECTION)
  const [mounted, setMounted] = useState(false)
  const [pairs, setPairs] = useState<PairSnapshot[]>([])
  const [entries, setEntries] = useState<DetectedEntry[]>([])
  const [selectedEntryIds, setSelectedEntryIds] = useState<string[]>([])
  const [showEntries, setShowEntries] = useState(false)
  const [telegramPending, setTelegramPending] = useState(false)
  const [telegramMessage, setTelegramMessage] = useState<string | null>(null)
  const [telegramError, setTelegramError] = useState(false)
  const [status, setStatus] = useState<SocketStatus>('connecting')
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<string | null>(null)
  const [scanInterval, setScanInterval] = useState<number | null>(null)
  const [scanning, setScanning] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [localTime, setLocalTime] = useState(false)
  const [now, setNow] = useState(() => new Date())
  const socketRef = useRef<WebSocket | null>(null)
  const selectionRef = useRef(selection)
  const telegramPendingRef = useRef(false)
  const telegramTimeoutRef = useRef<number | null>(null)

  function finishTelegramDispatch(message?: string) {
    if (telegramTimeoutRef.current !== null) {
      window.clearTimeout(telegramTimeoutRef.current)
      telegramTimeoutRef.current = null
    }
    telegramPendingRef.current = false
    setTelegramPending(false)
    if (message) {
      setTelegramError(true)
      setTelegramMessage(message)
    }
  }

  function sendConfiguration(socket: WebSocket, modules: ModuleSelection) {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'configure', modules }))
    }
  }

  function updateModule(id: ModuleKey, checked: boolean) {
    const next = { ...selectionRef.current, [id]: checked }
    selectionRef.current = next
    setSelection(next)
    const socket = socketRef.current
    if (socket) sendConfiguration(socket, next)
  }

  function updateAllModules(enabled: boolean) {
    const next = Object.fromEntries(MODULES.map(({ id }) => [id, enabled])) as ModuleSelection
    selectionRef.current = next
    setSelection(next)
    const socket = socketRef.current
    if (socket) sendConfiguration(socket, next)
  }

  function requestScan() {
    const socket = socketRef.current
    if (socket?.readyState === WebSocket.OPEN) {
      setScanning(true)
      socket.send(JSON.stringify({ type: 'refresh' }))
    } else {
      setError('The scanner is not connected. Reconnect before requesting a scan.')
    }
  }

  function dispatchEntries(mode: 'all' | 'selected') {
    const socket = socketRef.current
    if (socket?.readyState !== WebSocket.OPEN) {
      setTelegramError(true)
      setTelegramMessage('The scanner is not connected. Reconnect before sending entries.')
      return
    }
    if (mode === 'selected' && (selectedEntryIds.length < 1 || selectedEntryIds.length > 2)) {
      setTelegramError(true)
      setTelegramMessage('Select one or two active setups before sending.')
      return
    }
    setTelegramPending(true)
    telegramPendingRef.current = true
    setTelegramError(false)
    setTelegramMessage(null)
    try {
      socket.send(JSON.stringify({
        type: 'telegram_dispatch',
        mode,
        ...(mode === 'selected' ? { entry_ids: selectedEntryIds } : {}),
      }))
      telegramTimeoutRef.current = window.setTimeout(() => {
        finishTelegramDispatch(
          'Telegram dispatch timed out; delivery status is unknown. Check your Telegram chat before retrying.',
        )
      }, 30000)
    } catch {
      finishTelegramDispatch('Could not send the Telegram dispatch request. Check the scanner connection and retry.')
    }
  }

  function toggleEntry(entryId: string) {
    setSelectedEntryIds((selected) => {
      if (selected.includes(entryId)) return selected.filter((id) => id !== entryId)
      if (selected.length >= 2) return selected
      return [...selected, entryId]
    })
  }

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    let socket: WebSocket | undefined
    let retryTimer: number | undefined
    let heartbeatTimer: number | undefined
    let retries = 0
    let disposed = false

    function scheduleReconnect() {
      if (disposed) return
      const delay = Math.min(1000 * 2 ** retries, 10000)
      retries += 1
      retryTimer = window.setTimeout(connect, delay)
    }

    function connect() {
      if (disposed) return
      setStatus(retries === 0 ? 'connecting' : 'reconnecting')
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const url =
        process.env.NEXT_PUBLIC_API_WS_URL ||
        `${protocol}//${window.location.hostname}:8000/api/ws/dashboard`

      let currentSocket: WebSocket
      try {
        currentSocket = new WebSocket(url)
        socket = currentSocket
        socketRef.current = currentSocket
      } catch {
        setError('Could not create the scanner WebSocket connection.')
        setStatus('reconnecting')
        scheduleReconnect()
        return
      }

      let lastPongAt = 0
      currentSocket.onopen = () => {
        if (disposed || socketRef.current !== currentSocket) return
        lastPongAt = Date.now()
        setStatus('connected')
        setError(null)
        sendConfiguration(currentSocket, selectionRef.current)
        heartbeatTimer = window.setInterval(() => {
          if (disposed || socketRef.current !== currentSocket) return
          if (currentSocket.readyState !== WebSocket.OPEN) return
          if (Date.now() - lastPongAt > HEARTBEAT_TIMEOUT_MS) {
            setStatus('reconnecting')
            currentSocket.close()
            return
          }
          try {
            currentSocket.send(JSON.stringify({ type: 'ping' }))
          } catch {
            currentSocket.close()
          }
        }, HEARTBEAT_INTERVAL_MS)
      }
      currentSocket.onmessage = (event: MessageEvent<string>) => {
        if (disposed || socketRef.current !== currentSocket) return
        let message: unknown
        try {
          message = JSON.parse(event.data)
        } catch {
          setError('The scanner returned an unreadable response.')
          setScanning(false)
          return
        }
        if (isRecord(message) && message.type === 'pong') {
          lastPongAt = Date.now()
          retries = 0
          setStatus('connected')
          setError(null)
          return
        }
        if (isRecord(message) && message.type === 'error' && typeof message.message === 'string') {
          setError(message.message)
          setScanning(false)
          return
        }
        if (isRecord(message) && message.type === 'telegram_result') {
          finishTelegramDispatch()
          setTelegramError(message.ok !== true)
          setTelegramMessage(
            typeof message.message === 'string' ? message.message : 'Telegram dispatch returned an invalid response.',
          )
          return
        }
        if (!isDashboardMessage(message)) {
          setError('The scanner returned a response in an unexpected format.')
          setScanning(false)
          return
        }
        lastPongAt = Date.now()
        retries = 0
        setStatus('connected')
        setPairs(message.pairs)
        const detectedEntries = Array.isArray(message.entries)
          ? message.entries.filter(isDetectedEntry)
          : []
        setEntries(detectedEntries)
        setSelectedEntryIds((selected) =>
          selected.filter((id) => detectedEntries.some((entry) => entry.id === id)),
        )
        setLastUpdate(typeof message.generated_at === 'string' ? message.generated_at : null)
        setScanInterval(
          typeof message.scan_interval_seconds === 'number'
            ? message.scan_interval_seconds
            : null,
        )
        setScanning(false)
        setError(null)
      }
      currentSocket.onerror = () => {
        if (disposed || socketRef.current !== currentSocket) return
        setStatus('reconnecting')
        setError('Scanner connection failed. Retrying…')
        if (telegramPendingRef.current) {
          finishTelegramDispatch(
            'Scanner connection dropped during Telegram dispatch; delivery status is unknown. Check your Telegram chat before retrying.',
          )
        }
        currentSocket.close()
      }
      currentSocket.onclose = () => {
        if (socketRef.current !== currentSocket) return
        socketRef.current = null
        if (heartbeatTimer !== undefined) {
          window.clearInterval(heartbeatTimer)
          heartbeatTimer = undefined
        }
        if (telegramPendingRef.current) {
          finishTelegramDispatch(
            'Scanner disconnected before confirming Telegram delivery. Check your Telegram chat before retrying.',
          )
        }
        if (disposed) return
        setStatus('reconnecting')
        setScanning(false)
        scheduleReconnect()
      }
    }

    connect()
    return () => {
      disposed = true
      if (retryTimer !== undefined) window.clearTimeout(retryTimer)
      if (heartbeatTimer !== undefined) window.clearInterval(heartbeatTimer)
      if (telegramTimeoutRef.current !== null) window.clearTimeout(telegramTimeoutRef.current)
      if (socketRef.current === socket) socketRef.current = null
      socket?.close()
    }
  }, [])

  const livePairs = pairs.filter((pair) => pair.status === 'CONNECTED')
  const signalCount = livePairs.reduce(
    (count, pair) =>
      count +
      MODULES.filter(
        ({ id }) => selection[id] && pair.modules?.[id]?.signal != null,
      ).length,
    0,
  )
  const clock = mounted
    ? now.toLocaleTimeString(undefined, {
    ...(localTime ? {} : { timeZone: 'UTC' }),
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
      })
    : '--:--:--'

  function scrollTo(id: string) {
    setMobileNavOpen(false)
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <main className="app-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <aside className={`sidebar ${mobileNavOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><span /></div>
          <div><strong>ICT<span>•</span>2.0</strong><small>SCANNER CONTROL ROOM</small></div>
          <button className="mobile-close" onClick={() => setMobileNavOpen(false)} aria-label="Close menu">
            <X />
          </button>
        </div>
        <div className="workspace">
          <div className="workspace-icon"><Activity /></div>
          <div><span>DATA MODE</span><strong>Configured live providers</strong></div>
        </div>
        <nav className="nav-list" aria-label="Dashboard sections">
          <p className="nav-label">SCANNER</p>
          <button className="nav-item nav-item-active" onClick={() => scrollTo('overview')}>
            <Radio /> Overview
          </button>
          <button className="nav-item" onClick={() => scrollTo('entry-models')}>
            <Settings2 /> Entry models
          </button>
          <button className="nav-item" onClick={() => scrollTo('live-feeds')}>
            <Activity /> Live feeds
          </button>
        </nav>
        <div className="sidebar-bottom">
          <div className="system-card">
            <div className="system-icon"><ShieldCheck /></div>
            <div>
              <strong>{status === 'connected' ? 'Scanner API connected' : 'Scanner API unavailable'}</strong>
              <span><i className={`status-dot ${status === 'connected' ? 'status-dot-green' : 'status-dot-yellow'}`} />{livePairs.length} real feeds connected</span>
            </div>
          </div>
          <div className="user-row"><div className="avatar">ICT</div><div><strong>Local workspace</strong><span>Live provider data only</span></div></div>
        </div>
      </aside>

      <section className="content-area">
        <header className="topbar">
          <button className="mobile-menu" onClick={() => setMobileNavOpen(true)} aria-label="Open menu"><Menu /></button>
          <div className="breadcrumb"><span>Scanner</span><ChevronRight /><strong>Control room</strong></div>
          <div className="top-actions">
            <div className="utc-clock">
              <Clock3 /><span>{clock} <b>{localTime ? 'LOCAL' : 'UTC'}</b></span>
              <button onClick={() => setLocalTime((value) => !value)} aria-label="Toggle time zone"><RefreshCw /></button>
            </div>
            <span className="connection">
              <i className={status === 'connected' ? '' : 'connection-idle'} />
              {status === 'connected' ? 'Connected' : status === 'connecting' ? 'Connecting' : 'Reconnecting'}
            </span>
            <button className="scan-button" onClick={requestScan} disabled={scanning || status !== 'connected'}>
              <Play data-icon="inline-start" />{scanning ? 'Scanning…' : 'Scan now'}
            </button>
          </div>
        </header>

        <div className="page-content" id="overview">
          <div className="page-heading">
            <div>
              <div className="eyebrow"><span className="eyebrow-dot" /> REAL PROVIDER CANDLES · NO SYNTHETIC FALLBACK</div>
              <h1>Live ICT Control Room</h1>
              <p>Module controls recalculate closed candles from each active pair&apos;s configured provider.</p>
            </div>
            <div className="session-pill">
              <span className="session-orb" />
              <div><small>LAST BACKEND UPDATE</small><strong>{lastUpdate ? new Date(lastUpdate).toLocaleTimeString(undefined, { timeZone: 'UTC' }) + ' UTC' : 'Waiting for feed'}</strong></div>
              <Check />
            </div>
          </div>

          {error && <div className="dashboard-error" role="alert">{error}</div>}
          {telegramMessage && (
            <div className={telegramError ? 'dashboard-error' : 'dashboard-notice'} role={telegramError ? 'alert' : 'status'}>
              {telegramMessage}
            </div>
          )}

          <div className="stat-grid">
            <div className="stat-card glass-panel">
              <div className="stat-top"><span>REAL FEEDS</span><Radio /></div>
              <strong>{livePairs.length}<span>/{pairs.length}</span></strong>
              <div className="stat-bottom"><span>Provider candles connected</span></div>
            </div>
            <div className="stat-card glass-panel">
              <div className="stat-top"><span>ACTIVE MODULES</span><Settings2 /></div>
              <strong>{MODULES.filter(({ id }) => selection[id]).length}<span>/{MODULES.length}</span></strong>
              <div className="stat-bottom"><span>Selected on this dashboard</span></div>
            </div>
            <div className="stat-card glass-panel">
              <div className="stat-top"><span>DETECTED SIGNALS</span><Activity /></div>
              <strong>{signalCount}</strong>
              <div className="stat-bottom"><span>From latest closed candles</span></div>
            </div>
            <div className="stat-card glass-panel">
              <div className="stat-top"><span>REFRESH CADENCE</span><RefreshCw /></div>
              <strong>{scanInterval ?? '—'}<span>{scanInterval === null ? '' : 's'}</span></strong>
              <div className="stat-bottom"><span>Scan now or module changes refresh immediately</span></div>
            </div>
          </div>

          <section className="glass-panel module-panel" id="entry-models">
            <div className="section-title">
              <h2>Live entry model configuration</h2>
              <p>Every selection is sent to the backend immediately and triggers a fresh provider scan.</p>
            </div>
            <div className="module-actions">
              <button className="text-button" onClick={() => updateAllModules(true)}>Enable all</button>
              <button className="text-button" onClick={() => updateAllModules(false)}>Disable all</button>
              <button className="detected-entries-button" onClick={() => setShowEntries(true)}>
                All Detected Entries <span>{entries.length}</span>
              </button>
            </div>
            <div className="module-grid">
              {MODULES.map(({ id, label, detail }) => (
                <label className="module-toggle" key={id}>
                  <input
                    type="checkbox"
                    checked={selection[id]}
                    onChange={(event) => updateModule(id, event.target.checked)}
                  />
                  <span className="module-toggle-copy"><strong>{label}</strong><small>{detail}</small></span>
                </label>
              ))}
            </div>
          </section>

          {showEntries && (
            <div className="entries-modal-backdrop" onClick={(event) => {
              if (event.target === event.currentTarget) setShowEntries(false)
            }}>
              <section className="entries-modal glass-panel" role="dialog" aria-modal="true" aria-labelledby="entries-title">
                <div className="entries-modal-heading">
                  <div>
                    <h2 id="entries-title">All Detected Entries</h2>
                    <p>{entries.length} active setup{entries.length === 1 ? '' : 's'} across connected market pairs.</p>
                  </div>
                  <button className="icon-button" onClick={() => setShowEntries(false)} aria-label="Close detected entries">
                    <X />
                  </button>
                </div>
                <p className="entry-ranking-note">
                  “Best 2” prioritizes ready Master Sniper confluence, Unicorn, institutional order blocks, and
                  Silver Bullet, then other directional signals; measured displacement breaks ties. This is not a probability score.
                </p>
                <div className="entries-toolbar">
                  <button className="text-button" onClick={() => setSelectedEntryIds(entries.slice(0, 2).map((entry) => entry.id))} disabled={!entries.length}>
                    Select best 2 setups
                  </button>
                  <span>{selectedEntryIds.length}/2 selected</span>
                </div>
                <div className="detected-entry-list">
                  {entries.length === 0 ? (
                    <p className="empty-state">No active detected entries in the latest closed-candle scan.</p>
                  ) : entries.map((entry) => (
                    <label className="detected-entry" key={entry.id}>
                      <input
                        type="checkbox"
                        checked={selectedEntryIds.includes(entry.id)}
                        disabled={!selectedEntryIds.includes(entry.id) && selectedEntryIds.length >= 2}
                        onChange={() => toggleEntry(entry.id)}
                      />
                      <span className="detected-entry-copy">
                        <strong>{entry.symbol} · {entry.direction} · {entry.module_label}</strong>
                        <small>
                          {entry.entry === null ? 'Entry level not defined' : `Entry ${formatPrice(entry.entry)}`}
                          {entry.low !== null && entry.high !== null
                            ? ` · Zone ${formatPrice(entry.low)}–${formatPrice(entry.high)}`
                            : ''}
                          {entry.mean_threshold !== null ? ` · Mean ${formatPrice(entry.mean_threshold)}` : ''}
                        </small>
                        <small>{new Date(entry.timestamp).toLocaleString(undefined, { timeZone: 'UTC' })} UTC · {entry.provider}</small>
                      </span>
                    </label>
                  ))}
                </div>
                {telegramMessage && (
                  <div
                    className={telegramError ? 'dashboard-error' : 'dashboard-notice'}
                    role={telegramError ? 'alert' : 'status'}
                  >
                    {telegramMessage}
                  </div>
                )}
                <div className="entries-modal-actions">
                  <button className="text-button" onClick={() => dispatchEntries('all')} disabled={telegramPending || !entries.length}>
                    {telegramPending ? 'Sending…' : 'Send All Detected Entries to Telegram'}
                  </button>
                  <button
                    className="scan-button"
                    onClick={() => dispatchEntries('selected')}
                    disabled={telegramPending || selectedEntryIds.length < 1 || selectedEntryIds.length > 2}
                  >
                    Send Specific Selected Setups ({selectedEntryIds.length}/2)
                  </button>
                </div>
              </section>
            </div>
          )}

          <section className="section-row" id="live-feeds">
            <div className="section-title">
              <h2>Configured market feeds</h2>
              <p>Only closed OHLC candles returned by each active pair&apos;s provider are analyzed.</p>
            </div>
            <span className="live-label"><i /> {livePairs.length} LIVE</span>
          </section>
          {pairs.length === 0 ? (
            <div className="glass-panel empty-state">No active pairs are configured in the scanner database.</div>
          ) : (
            <div className="real-pair-grid">
              {pairs.map((pair) => (
                <article className="glass-panel real-pair-card" key={pair.symbol}>
                  <div className="real-pair-heading">
                    <div><h3>{pair.symbol}</h3><span>{pair.provider || 'Provider not configured'} · 5m</span></div>
                    <span className={`feed-status ${pair.status === 'CONNECTED' ? 'feed-status-live' : 'feed-status-offline'}`}>
                      {pair.status}
                    </span>
                  </div>
                  {pair.status === 'CONNECTED' && pair.candle ? (
                    <>
                      <p className="real-candle-time">{pair.timestamp ? new Date(pair.timestamp).toLocaleString(undefined, { timeZone: 'UTC' }) + ' UTC' : ''} · last closed candle</p>
                      <dl className="real-price-grid">
                        <div><dt>OPEN</dt><dd>{formatPrice(pair.candle.open)}</dd></div>
                        <div><dt>HIGH</dt><dd>{formatPrice(pair.candle.high)}</dd></div>
                        <div><dt>LOW</dt><dd>{formatPrice(pair.candle.low)}</dd></div>
                        <div><dt>CLOSE</dt><dd>{formatPrice(pair.candle.close)}</dd></div>
                      </dl>
                      <div className="pair-signals">
                        {MODULES.filter(({ id }) => selection[id] && pair.modules?.[id]?.signal).map(({ id, label }) => (
                          <div className="pair-signal" key={id}>
                            <strong>{label}</strong>
                            <span>{signalLines(pair.modules![id].signal!).join(' · ') || 'Detected'}</span>
                          </div>
                        ))}
                        {!MODULES.some(({ id }) => selection[id] && pair.modules?.[id]?.signal) && (
                          <p className="no-signal">No selected model has a signal in this closed-candle window.</p>
                        )}
                      </div>
                      {pair.advanced_ict && (
                        <div className="pair-signals advanced-ict-signals">
                          {Object.entries(pair.advanced_ict)
                            .filter(([, value]) => value !== null && value !== undefined)
                            .map(([key, value]) => {
                              const lines = Array.isArray(value)
                                ? value.flatMap(advancedSignalLines)
                                : advancedSignalLines(value)
                              if (lines.length === 0) return null
                              return (
                                <div className="pair-signal" key={key}>
                                  <strong>{key.replaceAll('_', ' ')}</strong>
                                  <span>{lines.join(' · ')}</span>
                                </div>
                              )
                            })}
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="feed-error">{pair.error || 'Waiting for provider data.'}</p>
                  )}
                </article>
              ))}
            </div>
          )}
          <footer>
            <span>ICT<span>•</span>2.0 CONTROL ROOM</span>
            <span>Market data and model signals are informational, not financial advice.</span>
            <span className="footer-status"><i />{status === 'connected' ? 'Backend connected' : 'Waiting for backend'}</span>
          </footer>
        </div>
      </section>
    </main>
  )
}
