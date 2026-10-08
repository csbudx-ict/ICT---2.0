'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  Bot,
  CalendarDays,
  ChevronRight,
  CircleHelp,
  Clock3,
  Command,
  Crosshair,
  Database,
  Gauge,
  LayoutDashboard,
  ListFilter,
  Menu,
  Network,
  PanelLeft,
  Play,
  Radio,
  RefreshCw,
  Search,
  Settings2,
  Sun,
  Moon,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Active Setups', icon: Crosshair, count: '06' },
  { label: 'History', icon: ListFilter },
  { label: 'Statistics', icon: BarChart3 },
  { label: 'Pairs', icon: Network },
  { label: 'Settings', icon: Settings2 },
  { label: 'Logs', icon: Database },
]

const pairs = [
  { symbol: 'EUR/USD', status: 'HEALTHY', time: '14:28:42', latency: '82ms' },
  { symbol: 'GBP/USD', status: 'HEALTHY', time: '14:28:38', latency: '94ms' },
  { symbol: 'USD/JPY', status: 'DEGRADED', time: '14:27:51', latency: '320ms' },
  { symbol: 'XAU/USD', status: 'HEALTHY', time: '14:28:40', latency: '76ms' },
  { symbol: 'NAS100', status: 'HEALTHY', time: '14:28:39', latency: '110ms' },
  { symbol: 'BTC/USDT', status: 'HEALTHY', time: '14:28:43', latency: '48ms' },
]

const setups = [
  { symbol: 'EUR/USD', direction: 'SHORT', probability: 82, entry: '1.08472', sl: '1.08618', tp1: '1.08182', tp2: '1.07956', rr: '2.0R', status: 'PENDING', session: 'NY AM', tf: '5m', tone: 'red' },
  { symbol: 'XAU/USD', direction: 'LONG', probability: 79, entry: '2,326.40', sl: '2,320.80', tp1: '2,337.60', tp2: '2,345.20', rr: '2.0R', status: 'TRIGGERED', session: 'NY AM', tf: '15m', tone: 'green' },
  { symbol: 'GBP/JPY', direction: 'SHORT', probability: 76, entry: '201.842', sl: '202.126', tp1: '201.274', tp2: '200.812', rr: '2.1R', status: 'PENDING', session: 'London', tf: '5m', tone: 'red' },
]

function StatusDot({ status }: { status: string }) {
  return <span className={cn('status-dot', status === 'HEALTHY' && 'status-dot-green', status === 'DEGRADED' && 'status-dot-yellow', status === 'STALE' && 'status-dot-red')} aria-label={status.toLowerCase()} />
}

function Sparkline({ positive = true }: { positive?: boolean }) {
  const points = positive ? '0,42 16,35 31,39 48,25 62,31 79,20 95,24 112,13 128,17 145,7' : '0,10 16,17 31,12 48,25 62,21 79,32 95,27 112,39 128,31 145,42'
  return <svg className="sparkline" viewBox="0 0 145 48" role="img" aria-label="performance trend"><polyline points={points} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
}

function MiniChart({ tone }: { tone: 'red' | 'green' }) {
  const bars = [34, 48, 29, 52, 41, 67, 55, 74, 61, 82, 70, 88]
  return (
    <div className="mini-chart" aria-label="Annotated price chart">
      <div className="chart-grid" />
      <div className={cn('chart-zone', tone === 'green' ? 'zone-green' : 'zone-red')} />
      <div className="chart-line" />
      <div className="candles">{bars.map((height, index) => <span key={index} className={cn('candle', index % 3 === 0 ? 'down' : 'up')} style={{ height: `${height}%` }} />)}</div>
      <div className="chart-label chart-label-entry">ENTRY</div>
      <div className="chart-label chart-label-fvg">FVG</div>
    </div>
  )
}

export default function Page() {
  const [activeNav, setActiveNav] = useState('Overview')
  const [mobileNav, setMobileNav] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [lastScan, setLastScan] = useState('14:28:44 UTC')
  const [localTime, setLocalTime] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light'>('light')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  const currentTime = useMemo(() => localTime ? '10:28:44 AM' : '14:28:44', [localTime])

  function runScan() {
    setScanning(true)
    window.setTimeout(() => { setScanning(false); setLastScan('just now') }, 900)
  }

  return (
    <main className="app-shell">
      <div className="ambient ambient-one" /><div className="ambient ambient-two" />
      <aside className={cn('sidebar', mobileNav && 'sidebar-open')}>
        <div className="brand"><div className="brand-mark"><span /></div><div><strong>ICT<span>•</span>2.0</strong><small>SCANNER CONTROL ROOM</small></div><button className="mobile-close" onClick={() => setMobileNav(false)} aria-label="Close menu"><X /></button></div>
        <div className="workspace"><div className="workspace-icon"><Command /></div><div><span>WORKSPACE</span><strong>Personal Desk</strong></div><ChevronRight className="chevron" /></div>
        <nav className="nav-list" aria-label="Primary navigation">
          <p className="nav-label">MONITORING</p>
          {navItems.slice(0, 4).map(item => <button key={item.label} className={cn('nav-item', activeNav === item.label && 'nav-item-active')} onClick={() => { setActiveNav(item.label); setMobileNav(false) }}><item.icon />{item.label}{item.count && <b>{item.count}</b>}{activeNav === item.label && <span className="active-line" />}</button>)}
          <p className="nav-label nav-label-space">CONFIGURATION</p>
          {navItems.slice(4).map(item => <button key={item.label} className={cn('nav-item', activeNav === item.label && 'nav-item-active')} onClick={() => { setActiveNav(item.label); setMobileNav(false) }}><item.icon />{item.label}{activeNav === item.label && <span className="active-line" />}</button>)}
        </nav>
        <div className="sidebar-bottom"><div className="system-card"><div className="system-icon"><ShieldCheck /></div><div><strong>All systems nominal</strong><span><StatusDot status="HEALTHY" /> API connected</span></div></div><div className="user-row"><div className="avatar">JD</div><div><strong>Jordan Davis</strong><span>Pro workspace</span></div><SlidersHorizontal className="user-settings" /></div></div>
      </aside>

      <section className="content-area">
        <header className="topbar"><button className="mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open menu"><Menu /></button><div className="breadcrumb"><span>Control room</span><ChevronRight /><strong>{activeNav}</strong></div><div className="top-actions"><div className="utc-clock"><Clock3 /><span>{currentTime} <b>{localTime ? 'LOCAL' : 'UTC'}</b></span><button onClick={() => setLocalTime(!localTime)} aria-label="Toggle time zone"><RefreshCw /></button></div><span className="connection"><i /> Live</span><button className="icon-button" aria-label="Notifications"><Bell /><i /></button><button className="icon-button theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>{theme === 'dark' ? <Sun /> : <Moon />}</button><button className="scan-button" onClick={runScan} disabled={scanning}><Play data-icon="inline-start" />{scanning ? 'Scanning…' : 'Scan now'}</button></div></header>
        <div className="page-content">
          <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-dot" /> THURSDAY, OCTOBER 8, 2026</div><h1>Good afternoon, Jordan <span>↗</span></h1><p>Here&apos;s what&apos;s moving across your markets.</p></div><div className="session-pill"><span className="session-orb" /><div><small>ACTIVE KILL ZONE</small><strong>NY AM <em>•</em> 01:32 remaining</strong></div><Zap /></div></div>

          <section className="health-strip glass-panel"><div className="strip-heading"><Radio /><span>FEED HEALTH</span><b>5/6 LIVE</b></div>{pairs.map(pair => <div className="feed-pair" key={pair.symbol}><StatusDot status={pair.status} /><strong>{pair.symbol}</strong><span>{pair.time}</span><small>{pair.latency}</small></div>)}<button className="health-more" aria-label="View feed health"><ChevronRight /></button></section>

          <div className="stat-grid"><div className="stat-card glass-panel"><div className="stat-top"><span>WIN RATE</span><TrendingUp className="icon-green" /></div><strong>68.4<span>%</span></strong><div className="stat-bottom"><span className="positive">+4.2%</span><span>vs last 30 days</span><Sparkline /></div></div><div className="stat-card glass-panel"><div className="stat-top"><span>AVERAGE R</span><Gauge /></div><strong>+1.72<span>R</span></strong><div className="stat-bottom"><span className="positive">+0.34R</span><span>vs last 30 days</span><Sparkline /></div></div><div className="stat-card glass-panel"><div className="stat-top"><span>SETUPS TODAY</span><Crosshair /></div><strong>12</strong><div className="stat-bottom"><span className="neutral">06 active</span><span>18% above avg.</span><div className="stat-bars">{[34, 56, 43, 67, 52, 78, 63, 89].map((h, i) => <i key={i} style={{ height: `${h}%` }} />)}</div></div></div><div className="stat-card glass-panel"><div className="stat-top"><span>ALERTS SENT</span><Bell /></div><strong>28</strong><div className="stat-bottom"><span className="positive">98.1% delivered</span><span>this session</span><div className="delivery-ring"><span>98</span></div></div></div></div>

          <div className="section-row"><div className="section-title"><h2>Active setups <span>06</span></h2><p>Highest conviction opportunities right now</p></div><button className="text-button" onClick={() => setActiveNav('Active Setups')}>View all setups <ChevronRight /></button></div>
          <div className="setup-grid">{setups.map((setup, i) => <article className="setup-card glass-panel" key={setup.symbol}><div className="setup-card-head"><div className={cn('direction-chip', setup.tone === 'green' ? 'direction-long' : 'direction-short')}>{setup.tone === 'green' ? <TrendingUp /> : <TrendingDown />} {setup.direction}</div><span className={cn('lifecycle', setup.status === 'TRIGGERED' && 'lifecycle-triggered')}>{setup.status}</span><button className="more-button" aria-label={`More options for ${setup.symbol}`}>•••</button></div><MiniChart tone={setup.tone as 'red' | 'green'} /><div className="setup-info"><div><h3>{setup.symbol}</h3><span>{setup.session} <i /> {setup.tf} entry</span></div><div className="probability"><strong>{setup.probability}%</strong><span>CONFLUENCE</span></div></div><div className="price-grid"><div><span>ENTRY</span><strong>{setup.entry}</strong></div><div><span>STOP LOSS</span><strong className="text-red">{setup.sl}</strong></div><div><span>TP1</span><strong className="text-green">{setup.tp1}</strong></div><div><span>TP2</span><strong className="text-green">{setup.tp2}</strong></div></div><div className="setup-footer"><span><Target /> {setup.rr} to TP1</span><span><Clock3 /> Expires in <b>{i === 1 ? '01:42:18' : '02:18:42'}</b></span></div></article>)}</div>

          <div className="bottom-grid"><section className="equity-card glass-panel"><div className="card-heading"><div><h2>Equity curve</h2><p>Cumulative performance in R</p></div><div className="period-tabs"><button className="active">30D</button><button>90D</button><button>ALL</button></div></div><div className="equity-summary"><strong>+18.42R</strong><span className="positive">+12.8% <small>vs previous</small></span></div><div className="equity-chart"><div className="y-labels"><span>20R</span><span>10R</span><span>0</span><span>-10R</span></div><svg viewBox="0 0 650 175" preserveAspectRatio="none" aria-label="Cumulative equity curve"><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#3dd9b3" stopOpacity=".25" /><stop offset="1" stopColor="#3dd9b3" stopOpacity="0" /></linearGradient></defs><path d="M0 148 C20 145, 28 125, 47 131 S72 139, 89 110 S117 120, 136 106 S159 114, 179 93 S204 98, 221 77 S246 90, 267 72 S292 82, 312 58 S336 70, 355 54 S381 71, 404 42 S429 49, 451 32 S475 46, 498 27 S521 38, 543 18 S569 28, 592 11 S623 24, 650 3 L650 175 L0 175Z" fill="url(#area)" /><path d="M0 148 C20 145, 28 125, 47 131 S72 139, 89 110 S117 120, 136 106 S159 114, 179 93 S204 98, 221 77 S246 90, 267 72 S292 82, 312 58 S336 70, 355 54 S381 71, 404 42 S429 49, 451 32 S475 46, 498 27 S521 38, 543 18 S569 28, 592 11 S623 24, 650 3" fill="none" stroke="#3dd9b3" strokeWidth="2.5" /></svg><div className="x-labels"><span>SEP 09</span><span>SEP 16</span><span>SEP 23</span><span>SEP 30</span><span>OCT 08</span></div></div></section><section className="activity-card glass-panel"><div className="card-heading"><div><h2>Live activity</h2><p>System events and AI observations</p></div><span className="live-label"><i /> LIVE</span></div><div className="activity-list"><div className="activity-item"><div className="activity-icon green"><TrendingUp /></div><div><strong>TP1 hit on GBP/JPY</strong><p>Position moved to risk-free · +1.0R</p></div><time>2m ago</time></div><div className="activity-item"><div className="activity-icon violet"><Bot /></div><div><strong>AI found new confluence</strong><p>Liquidity sweep on EUR/USD · waiting for MSS</p></div><time>5m ago</time></div><div className="activity-item"><div className="activity-icon yellow"><AlertTriangle /></div><div><strong>Feed latency increased</strong><p>USD/JPY is currently degraded · 320ms</p></div><time>9m ago</time></div><div className="activity-item"><div className="activity-icon blue"><RefreshCw /></div><div><strong>Market scan completed</strong><p>12 setups found across 6 pairs</p></div><time>{lastScan}</time></div></div></section></div>
          <footer><span>ICT<span>•</span>2.0 CONTROL ROOM</span><span>Informational only. Not financial advice.</span><span className="footer-status"><i /> Systems operational</span></footer>
        </div>
      </section>
    </main>
  )
}
