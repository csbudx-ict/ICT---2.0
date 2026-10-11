'use client'

import { useEffect, useRef, useState } from 'react'

const MODULES = [
  { id: 'unicorn_setup', label: 'Unicorn Setup (Breaker Block + FVG)' },
  { id: 'silver_bullet_fvg', label: 'Silver Bullet / Fair Value Gap' },
  { id: 'institutional_order_block', label: 'Institutional Order Block (50% Mean Threshold)' },
  { id: 'breaker_blocks', label: 'Breaker Blocks' },
  { id: 'ote_fibonacci', label: 'OTE Fibonacci (0.618–0.790 / 0.705 sweet spot)' },
  { id: 'premium_discount', label: 'Premium / Discount Equilibrium' },
  { id: 'box_liquidity', label: 'BOX / Liquidity' },
] as const

type ModuleKey = (typeof MODULES)[number]['id']
type ModuleSelection = Record<ModuleKey, boolean>
type ModuleSignal = Record<string, unknown>
type ModuleSnapshot = { enabled: boolean; signal: ModuleSignal | null }
type Candle = {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
}
type SymbolUpdate = {
  symbol: string
  status: 'live' | 'unavailable'
  timeframe?: string
  price?: number
  candle?: Candle
  modules?: Record<ModuleKey, ModuleSnapshot>
  error?: string
}
type MarketUpdate = {
  type: 'market_update'
  provider: 'Twelve Data'
  generated_at: string
  poll_interval_seconds: number
  symbols: SymbolUpdate[]
}
type ConnectionStatus = 'connecting' | 'live' | 'reconnecting'

const DEFAULT_SELECTION: ModuleSelection = Object.fromEntries(
  MODULES.map(({ id }) => [id, true]),
) as ModuleSelection
const SYMBOLS = ['EUR/USD', 'GBP/USD', 'XAU/USD']

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isSymbolUpdate(value: unknown): value is SymbolUpdate {
  return (
    isRecord(value) &&
    typeof value.symbol === 'string' &&
    (value.status === 'live' || value.status === 'unavailable')
  )
}

function isMarketUpdate(value: unknown): value is MarketUpdate {
  return (
    isRecord(value) &&
    value.type === 'market_update' &&
    value.provider === 'Twelve Data' &&
    typeof value.generated_at === 'string' &&
    typeof value.poll_interval_seconds === 'number' &&
    Array.isArray(value.symbols) &&
    value.symbols.every(isSymbolUpdate)
  )
}

function utcTime(timestamp: string) {
  return new Date(timestamp).toLocaleTimeString(undefined, {
    timeZone: 'UTC',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatPrice(value: number | undefined, symbol: string) {
  if (value === undefined) return '—'
  return value.toFixed(symbol === 'XAU/USD' ? 2 : 5)
}

function summarizeSignal(signal: ModuleSignal): string[] {
  return Object.entries(signal)
    .filter(([, value]) => ['string', 'number', 'boolean'].includes(typeof value))
    .map(([key, value]) =>
      typeof value === 'number'
        ? `${key.replaceAll('_', ' ')}: ${value.toFixed(5)}`
        : `${key.replaceAll('_', ' ')}: ${String(value)}`,
    )
}

export default function LiveEurusdDemo() {
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [updates, setUpdates] = useState<Record<string, SymbolUpdate>>({})
  const [selection, setSelection] = useState<ModuleSelection>(DEFAULT_SELECTION)
  const [error, setError] = useState<string | null>(null)
  const [pollInterval, setPollInterval] = useState<number | null>(null)
  const [lastUpdated, setLastUpdated] = useState<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const selectionRef = useRef(selection)

  function sendSelection(socket: WebSocket) {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'configure', modules: selectionRef.current }))
    }
  }

  function updateSelection(next: ModuleSelection) {
    selectionRef.current = next
    setSelection(next)
    if (socketRef.current) sendSelection(socketRef.current)
  }

  function toggleModule(module: ModuleKey) {
    updateSelection({ ...selectionRef.current, [module]: !selectionRef.current[module] })
  }

  useEffect(() => {
    let socket: WebSocket | undefined
    let retryTimer: number | undefined
    let retryCount = 0
    let disposed = false

    function scheduleReconnect() {
      if (disposed) return
      const delay = Math.min(1000 * 2 ** retryCount, 10000)
      retryCount += 1
      retryTimer = window.setTimeout(connect, delay)
    }

    function connect() {
      if (disposed) return
      setStatus(retryCount === 0 ? 'connecting' : 'reconnecting')
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const defaultUrl = `${protocol}//${window.location.hostname}:8000/api/ws/live-market`

      try {
        socket = new WebSocket(process.env.NEXT_PUBLIC_API_WS_URL || defaultUrl)
        socketRef.current = socket
      } catch {
        setError('Could not create the Twelve Data WebSocket connection.')
        scheduleReconnect()
        return
      }

      socket.onopen = () => {
        retryCount = 0
        setStatus('live')
        setError(null)
        sendSelection(socket!)
      }
      socket.onmessage = (event: MessageEvent<string>) => {
        let message: unknown
        try {
          message = JSON.parse(event.data)
        } catch {
          setError('The backend sent an unreadable market update.')
          return
        }
        if (isRecord(message) && message.type === 'error' && typeof message.message === 'string') {
          setError(message.message)
          return
        }
        if (!isMarketUpdate(message)) {
          setError('The backend sent a market update in an unexpected format.')
          return
        }
        const received = Object.fromEntries(
          message.symbols.map((symbol) => [symbol.symbol, symbol]),
        )
        setUpdates((current) => ({ ...current, ...received }))
        setPollInterval(message.poll_interval_seconds)
        setLastUpdated(message.generated_at)
        const unavailable = message.symbols.filter((symbol) => symbol.status === 'unavailable')
        setError(
          unavailable.length > 0
            ? unavailable.map(({ symbol, error: reason }) => `${symbol}: ${reason}`).join(' · ')
            : null,
        )
      }
      socket.onerror = () => setError('Twelve Data connection failed. Retrying…')
      socket.onclose = () => {
        socketRef.current = null
        if (disposed) return
        setStatus('reconnecting')
        scheduleReconnect()
      }
    }

    connect()
    return () => {
      disposed = true
      if (retryTimer !== undefined) window.clearTimeout(retryTimer)
      socketRef.current = null
      socket?.close()
    }
  }, [])

  return (
    <main className="min-h-screen bg-[#070b14] px-5 py-12 text-[#edf2fa] sm:px-8">
      <div className="mx-auto max-w-6xl">
        <a className="text-sm text-[#56d9ee] hover:underline" href="/">
          ← Back to scanner dashboard
        </a>
        <header className="mt-8 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#56d9ee]">
              Twelve Data · closed 1-minute candles
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
              Live ICT market scanner
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
              EUR/USD, GBP/USD, and XAU/USD are polled from the backend Twelve Data client. Only
              completed provider candles are sent to the ICT engine; no synthetic fallback is used.
            </p>
          </div>
          <div
            className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-2 text-sm"
            role="status"
            aria-live="polite"
          >
            <span
              className={`h-2 w-2 rounded-full ${
                status === 'live' ? 'bg-emerald-400' : 'bg-amber-400'
              }`}
            />
            {status === 'live' ? 'Backend connected' : status === 'connecting' ? 'Connecting' : 'Reconnecting'}
          </div>
        </header>

        {error && (
          <p className="mt-6 rounded-lg border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </p>
        )}

        <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold">Seven live ICT modules</h2>
              <p className="mt-1 text-xs text-slate-500">
                Changes are sent over the dashboard WebSocket and recalculated against provider candles.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-300 hover:bg-white/[0.06]"
                onClick={() => updateSelection(Object.fromEntries(MODULES.map(({ id }) => [id, true])) as ModuleSelection)}
                type="button"
              >
                Enable all
              </button>
              <button
                className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-300 hover:bg-white/[0.06]"
                onClick={() => updateSelection(Object.fromEntries(MODULES.map(({ id }) => [id, false])) as ModuleSelection)}
                type="button"
              >
                Disable all
              </button>
            </div>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {MODULES.map(({ id, label }) => (
              <label
                className="flex cursor-pointer items-center gap-3 rounded-xl border border-white/[0.08] bg-black/10 px-4 py-3 text-sm"
                key={id}
              >
                <input
                  checked={selection[id]}
                  className="h-4 w-4 accent-cyan-300"
                  onChange={() => toggleModule(id)}
                  type="checkbox"
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        </section>

        <section className="mt-4 grid gap-4 lg:grid-cols-3">
          {SYMBOLS.map((symbol) => {
            const update = updates[symbol]
            return (
              <article
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-5"
                key={symbol}
              >
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-lg font-semibold">{symbol}</h2>
                  <span
                    className={`rounded-full px-2.5 py-1 text-[11px] ${
                      update?.status === 'live'
                        ? 'bg-emerald-300/10 text-emerald-200'
                        : update?.status === 'unavailable'
                          ? 'bg-amber-300/10 text-amber-200'
                          : 'bg-white/[0.06] text-slate-400'
                    }`}
                  >
                    {update?.status === 'live'
                      ? 'LIVE · 1M'
                      : update?.status === 'unavailable'
                        ? 'UNAVAILABLE'
                        : 'WAITING'}
                  </span>
                </div>
                {update?.status === 'live' && update.candle ? (
                  <>
                    <p className="mt-4 font-mono text-3xl font-semibold tabular-nums">
                      {formatPrice(update.price, symbol)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Closed candle · {utcTime(update.candle.timestamp)} UTC
                    </p>
                    <dl className="mt-5 grid grid-cols-4 gap-2 font-mono text-xs tabular-nums">
                      {(['open', 'high', 'low', 'close'] as const).map((key) => (
                        <div key={key}>
                          <dt className="font-sans text-[10px] uppercase text-slate-500">{key}</dt>
                          <dd className="mt-1">{formatPrice(update.candle?.[key], symbol)}</dd>
                        </div>
                      ))}
                    </dl>
                    <div className="mt-5 space-y-3 border-t border-white/10 pt-4">
                      {MODULES.map(({ id, label }) => {
                        const module = update.modules?.[id]
                        const signal = module?.signal
                        return (
                          <div className="text-xs" key={id}>
                            <div className="flex items-center justify-between gap-3">
                              <strong className="font-medium text-slate-300">{label}</strong>
                              <span className="text-slate-500">
                                {!selection[id] ? 'OFF' : signal ? 'DETECTED' : 'NO SIGNAL'}
                              </span>
                            </div>
                            {selection[id] && signal && (
                              <p className="mt-1 leading-5 text-slate-400">
                                {summarizeSignal(signal).join(' · ') || 'Signal detected'}
                              </p>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </>
                ) : (
                  <p className="mt-4 min-h-24 text-sm leading-6 text-slate-400">
                    {update?.error ?? 'Waiting for Twelve Data candle feed…'}
                  </p>
                )}
              </article>
            )
          })}
        </section>

        <footer className="mt-6 flex flex-wrap justify-between gap-2 text-xs text-slate-500">
          <span>
            {pollInterval
              ? `Twelve Data candle polling every ${pollInterval} seconds`
              : 'Waiting for initial provider poll'}
          </span>
          <span>
            {lastUpdated ? `Last backend update ${utcTime(lastUpdated)} UTC` : 'No provider update received'}
          </span>
        </footer>
      </div>
    </main>
  )
}
