import { useEffect, useState } from 'react'
import {
  ComposedChart, Line, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'

const getJson = (url) => fetch(url).then((r) => r.json())
const mw = (v) => (v == null ? '-' : Math.round(v).toLocaleString())

function Card({ label, value, hint }) {
  return (
    <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
      <div style={{ color: '#666', fontSize: 13 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 600 }}>{value}</div>
      {hint && <div style={{ color: '#888', fontSize: 12 }}>{hint}</div>}
    </div>
  )
}

export default function App() {
  const [day, setDay] = useState('2026-01-15')
  const [cutoff, setCutoff] = useState('09:00')
  const [fc, setFc] = useState(null)
  const [m, setM] = useState(null)
  const [hz, setHz] = useState([])
  const [daily, setDaily] = useState([])

  useEffect(() => { getJson(`/api/forecast?day=${day}&cutoff=${cutoff}`).then(setFc) }, [day, cutoff])
  useEffect(() => { getJson(`/api/metrics?cutoff=${cutoff}`).then(setM) }, [cutoff])
  useEffect(() => { getJson(`/api/daily-errors?cutoff=${cutoff}`).then(setDaily) }, [cutoff])
  useEffect(() => { getJson('/api/horizon-errors').then(setHz) }, [])

  const points = (fc?.points ?? []).map((p) => ({
    ...p,
    t: p.startTime.slice(11, 16),
    band: p.lo != null && p.hi != null ? [p.lo, p.hi] : null,
  }))
  const s = m?.summary

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: 24, fontFamily: 'system-ui, sans-serif' }}>
      <h1>GB Wind Forecast: Day-Ahead Decision Portal</h1>
      <p style={{ color: '#555' }}>
        What forecast was available when you had to buy, and how far off has it been? (January 2026, national wind, Elexon data)
      </p>

      <div style={{ display: 'flex', gap: 24, margin: '16px 0', flexWrap: 'wrap' }}>
        <label>Delivery day{' '}
          <input type="date" min="2026-01-02" max="2026-02-01" value={day} onChange={(e) => setDay(e.target.value)} />
        </label>
        <label>Decision cutoff (UK time, day before){' '}
          <input type="time" value={cutoff} onChange={(e) => setCutoff(e.target.value)} />
        </label>
      </div>

      {fc && (
        <p>
          Forecast used: published <b>{fc.publish_time ? fc.publish_time.replace('T', ' ').slice(0, 16) + ' UTC' : 'n/a'}</b>{' '}
          (latest before {fc.cutoff_utc.replace('T', ' ').slice(0, 16)} UTC).
          Shaded band: where actual output has typically landed (10th-90th percentile of past error).
        </p>
      )}

      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={points}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="t" interval={3} />
          <YAxis width={70} tickFormatter={mw} />
          <Tooltip formatter={(v) => (Array.isArray(v) ? `${mw(v[0])} - ${mw(v[1])}` : mw(v))} />
          <Legend />
          <Area dataKey="band" name="Typical range of actual" fill="#cfe3ff" stroke="none" connectNulls />
          <Line dataKey="forecast" name="Forecast (MW)" stroke="#1f6feb" dot={false} connectNulls />
          <Line dataKey="actual" name="Actual (MW)" stroke="#e5534b" dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
      <p style={{ color: '#777', fontSize: 13, marginTop: 4 }}>
        Forecast is hourly; actual generation is half-hourly. Times are UTC (same as UK time in January).
      </p>

      {s && (
        <>
          <h2>Forecast accuracy, delivery days 2 Jan - 1 Feb</h2>
          <p style={{ fontSize: 18 }}>
            The forecast was higher than actual output in <b>{s.pct_over.toFixed(0)}%</b> of hours,
            by <b>{mw(s.bias)} MW</b> on average.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            <Card label="Mean absolute error" value={`${mw(s.mae)} MW`} hint={`${s.mae_pct_of_mean.toFixed(1)}% of mean output`} />
            <Card label="RMSE" value={`${mw(s.rmse)} MW`} />
            <Card label="Bias (forecast - actual)" value={`${s.bias > 0 ? '+' : ''}${mw(s.bias)} MW`} hint="positive = forecast too high" />
            <Card label="Median abs error" value={`${mw(s.p50_abs)} MW`} />
            <Card label="90th percentile abs error" value={`${mw(s.p90_abs)} MW`} />
            <Card label="99th percentile abs error" value={`${mw(s.p99_abs)} MW`} />
          </div>
        </>
      )}

      <h3>Daily average error (click a bar to view that day)</h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={daily} onClick={(e) => e?.activeLabel && setDay(e.activeLabel)} style={{ cursor: 'pointer' }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="day" tickFormatter={(d) => d.slice(8)} />
          <YAxis tickFormatter={mw} width={70} />
          <Tooltip formatter={mw} />
          <ReferenceLine y={0} stroke="#333" />
          <Bar dataKey="bias" name="Mean error (MW, + = forecast too high)" fill="#e5534b" />
        </BarChart>
      </ResponsiveContainer>

      <h3>Error by hour of day (UK)</h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={m?.by_hour ?? []}>
          <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="hour" /><YAxis tickFormatter={mw} width={70} />
          <Tooltip formatter={mw} /><Legend />
          <Bar dataKey="mae" name="MAE (MW)" fill="#1f6feb" />
          <Bar dataKey="bias" name="Bias (MW)" fill="#e5534b" />
        </BarChart>
      </ResponsiveContainer>

      <h3>Error by forecast horizon (hours between publish and target)</h3>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={hz.map((h) => ({ ...h, label: `${h.horizon_from}-${h.horizon_to}h` }))}>
          <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="label" /><YAxis tickFormatter={mw} width={70} />
          <Tooltip formatter={mw} /><Legend />
          <Bar dataKey="mae" name="MAE (MW)" fill="#1f6feb" />
          <Bar dataKey="p90" name="P90 abs error (MW)" fill="#9bb8e8" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}