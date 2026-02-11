import React, { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
} from 'recharts'
import { api, API_BASE } from './api'

const statuses = ['Pending', 'Needs Review', 'Verified', 'Dispatched', 'Resolved', 'Rejected']
const severityColors = { Low: '#2bb673', Medium: '#f6a623', Critical: '#e84a5f' }

function Login({ onLogin }) {
  const [email, setEmail] = useState('responder@slsu.local')
  const [password, setPassword] = useState('password123')
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    try {
      const form = new FormData()
      form.append('email', email)
      form.append('password', password)
      const res = await fetch(`${API_BASE}/auth/login`, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Login failed')
      onLogin(data)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="center-wrap">
      <form className="card login" onSubmit={submit}>
        <h1>SLSU Responder Dashboard</h1>
        <p>Phase 2 Emergency Operations Console</p>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" />
        <button>Login</button>
        {error && <small className="error">{error}</small>}
      </form>
    </div>
  )
}

function MetricCard({ label, value }) {
  return (
    <div className="metric-card">
      <p>{label}</p>
      <h3>{value}</h3>
    </div>
  )
}

export default function App() {
  const [auth, setAuth] = useState(null)
  const [reports, setReports] = useState([])
  const [analytics, setAnalytics] = useState({ reports_per_type: [], severity_distribution: [], reports_over_time: [], flagged_users: [] })
  const [selected, setSelected] = useState(null)
  const [filters, setFilters] = useState({ severity: '', status: '', emergency_type: '' })
  const [error, setError] = useState('')

  const loadData = async (token = auth?.token) => {
    if (!token) return
    try {
      const [r, a] = await Promise.all([
        api('/reports', { token }),
        api('/reports/analytics', { token }),
      ])
      setReports(r)
      setAnalytics(a)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    if (auth?.token) loadData(auth.token)
  }, [auth?.token])

  const filtered = useMemo(() => reports.filter((r) => {
    return (!filters.severity || r.severity_label === filters.severity)
      && (!filters.status || r.status === filters.status)
      && (!filters.emergency_type || r.emergency_type.toLowerCase().includes(filters.emergency_type.toLowerCase()))
  }), [reports, filters])

  const metrics = useMemo(() => {
    const total = reports.length
    const critical = reports.filter((r) => r.severity_label === 'Critical').length
    const pending = reports.filter((r) => ['Pending', 'Needs Review'].includes(r.status)).length
    const resolved = reports.filter((r) => r.status === 'Resolved').length
    return { total, critical, pending, resolved }
  }, [reports])

  const setStatus = async (id, statusLabel) => {
    const form = new FormData()
    form.append('status_label', statusLabel)
    await fetch(`${API_BASE}/reports/${id}/status`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${auth.token}` },
      body: form,
    })
    await loadData()
  }

  const exportPdf = async () => {
    const res = await fetch(`${API_BASE}/reports/export/pdf`, {
      headers: { Authorization: `Bearer ${auth.token}` },
    })
    if (!res.ok) throw new Error('Export failed')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'emergency_reports_summary.pdf'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  if (!auth) return <Login onLogin={setAuth} />

  return (
    <div className="admin-shell">
      <aside className="sidebar">
        <h2>SLSU</h2>
        <p>Emergency Ops</p>
        <nav>
          <a>Overview</a>
          <a>Incidents</a>
          <a>Analytics</a>
          <a>Flagged Users</a>
        </nav>
        <button className="logout" onClick={() => setAuth(null)}>Logout</button>
      </aside>

      <section className="content">
        <header className="topbar">
          <h1>AI-Powered Emergency Response Dashboard</h1>
          <div className="right-actions">
            <button onClick={() => loadData()}>Refresh</button>
            <button onClick={exportPdf}>Export as PDF</button>
          </div>
        </header>

        <section className="metrics-grid">
          <MetricCard label="Total Reports" value={metrics.total} />
          <MetricCard label="Critical Cases" value={metrics.critical} />
          <MetricCard label="Pending Verification" value={metrics.pending} />
          <MetricCard label="Resolved Cases" value={metrics.resolved} />
        </section>

        <section className="filters card">
          <select onChange={(e) => setFilters({ ...filters, severity: e.target.value })}>
            <option value="">All Severity</option>
            <option>Low</option><option>Medium</option><option>Critical</option>
          </select>
          <select onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">All Status</option>
            {statuses.map((s) => <option key={s}>{s}</option>)}
          </select>
          <input placeholder="Emergency type" onChange={(e) => setFilters({ ...filters, emergency_type: e.target.value })} />
        </section>

        {error && <p className="error">{error}</p>}

        <section className="charts-grid">
          <div className="card chart-card">
            <h3>Reports per Emergency Type</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={analytics.reports_per_type || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" /><YAxis /><Tooltip /><Legend />
                <Bar dataKey="value" fill="#2d8cff" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card chart-card">
            <h3>Severity Distribution</h3>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={analytics.severity_distribution || []} dataKey="value" nameKey="name" outerRadius={85} label>
                  {(analytics.severity_distribution || []).map((entry) => (
                    <Cell key={entry.name} fill={severityColors[entry.name] || '#999'} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="card chart-card full">
            <h3>Reports Over Time</h3>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={analytics.reports_over_time || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" /><YAxis /><Tooltip /><Legend />
                <Line dataKey="value" stroke="#f14b5d" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        <main className="layout">
          <section className="card table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th><th>User</th><th>Type</th><th>Severity</th><th>Verify</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.id} onClick={() => setSelected(r)}>
                    <td>{new Date(r.created_at).toLocaleString()}</td>
                    <td>{r.reporter_email}</td>
                    <td>{r.emergency_type}</td>
                    <td><span className={`badge ${r.severity_label.toLowerCase()}`}>{r.severity_label}</span></td>
                    <td>{r.verification_score}</td>
                    <td>{r.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="card flagged-users">
            <h3>Flagged Users</h3>
            {(analytics.flagged_users || []).map((u) => (
              <div key={u.id} className="flag-item">
                <strong>{u.email}</strong>
                <span>Risk: {u.risk_score}</span>
              </div>
            ))}
            {!analytics.flagged_users?.length && <p>No flagged users.</p>}
          </section>
        </main>
      </section>

      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <div className="modal card" onClick={(e) => e.stopPropagation()}>
            <h3>Report #{selected.id} - {selected.emergency_type}</h3>
            <p><strong>User:</strong> {selected.reporter_email}</p>
            <p><strong>Description:</strong> {selected.description}</p>
            <p><strong>Severity:</strong> {selected.severity_label} ({selected.severity_confidence})</p>
            <p><strong>Verification:</strong> {selected.verification_score} | suspicious: {selected.suspicious ? 'yes' : 'no'}</p>
            <div className="img-row">
              <img src={`${API_BASE}${selected.selfie_url}`} alt="selfie" />
              <img src={`${API_BASE}${selected.accident_url}`} alt="accident" />
            </div>
            <iframe
              title="map"
              src={`https://maps.google.com/maps?q=${selected.latitude},${selected.longitude}&z=15&output=embed`}
              className="map-frame"
            />
            <div className="status-actions">
              <a href={`https://www.google.com/maps?q=${selected.latitude},${selected.longitude}`} target="_blank">Navigate</a>
              {['Verified', 'Dispatched', 'Resolved', 'Rejected'].map((s) => (
                <button key={s} onClick={() => setStatus(selected.id, s)}>{s}</button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
