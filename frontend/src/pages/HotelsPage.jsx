import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Plus, Edit2, Trash2, Wifi, Database, Router, Save, X, Zap, CheckCircle, AlertCircle, Loader, ChevronDown, ChevronUp } from 'lucide-react'

const DEFAULT = {
  name: '', hotspot_code: '',
  mssql_server: '', mssql_port: 1433, mssql_database: '', mssql_username: '', mssql_password: '',
  mssql_table_booking: 'PMS.RRVDATBL',
  mssql_col_booking_id: 'RESNUB', mssql_col_guest_name: 'GSTNAM', mssql_col_guest_phone: 'MBLNUB',
  mssql_col_room_number: 'ROOMNO', mssql_col_checkin: 'ARRIVL', mssql_col_checkout: 'DEPDAT',
  mssql_col_status: 'RSVSTS', mssql_col_status_confirmed: 'R,I',
  mikrotik_host: '', mikrotik_port: 8728, mikrotik_username: 'admin', mikrotik_password: '',
  mikrotik_hotspot_server: 'hotspot1', hotspot_password_length: 8,
  checkout_grace_minutes: 60, sync_enabled: true, sync_interval_minutes: 5,
}

export default function HotelsPage() {
  const [hotels, setHotels] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(DEFAULT)
  const [loading, setLoading] = useState(false)
  const [testResult, setTestResult] = useState({})
  const [detectResult, setDetectResult] = useState(null)
  const [detecting, setDetecting] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const load = async () => {
    const r = await api.get('/hotels/')
    setHotels(r.data)
  }

  useEffect(() => { load() }, [])

  const save = async () => {
    setLoading(true)
    try {
      if (editing) await api.put(`/hotels/${editing}`, form)
      else await api.post('/hotels/', form)
      setShowForm(false)
      setEditing(null)
      setForm(DEFAULT)
      setDetectResult(null)
      load()
    } catch (e) {
      alert(e.response?.data?.detail || 'Save failed')
    } finally { setLoading(false) }
  }

  const del = async (id) => {
    if (!confirm('Delete this hotel?')) return
    await api.delete(`/hotels/${id}`)
    load()
  }

  const testMssql = async (id) => {
    setTestResult(p => ({ ...p, [`mssql_${id}`]: 'loading' }))
    try {
      const r = await api.post(`/hotels/${id}/test-mssql`)
      setTestResult(p => ({ ...p, [`mssql_${id}`]: r.data.success ? 'ok' : 'fail_' + r.data.error }))
    } catch { setTestResult(p => ({ ...p, [`mssql_${id}`]: 'fail_Connection error' })) }
  }

  const testMikrotik = async (id) => {
    setTestResult(p => ({ ...p, [`mk_${id}`]: 'loading' }))
    try {
      const r = await api.post(`/hotels/${id}/test-mikrotik`)
      setTestResult(p => ({ ...p, [`mk_${id}`]: r.data.success ? 'ok' : 'fail_' + r.data.error }))
    } catch { setTestResult(p => ({ ...p, [`mk_${id}`]: 'fail_Connection error' })) }
  }

  const autoDetect = async () => {
    if (!editing) return
    setDetecting(true)
    setDetectResult(null)
    try {
      const r = await api.post(`/hotels/${editing}/auto-detect`)
      setDetectResult(r.data)
      if (r.data.success) {
        // Auto-apply detected values to form
        const cols = r.data.columns || {}
        setForm(prev => ({
          ...prev,
          mssql_table_booking: r.data.table || prev.mssql_table_booking,
          mssql_col_booking_id: cols.booking_id || prev.mssql_col_booking_id,
          mssql_col_guest_name: cols.guest_name || prev.mssql_col_guest_name,
          mssql_col_guest_phone: cols.guest_phone || prev.mssql_col_guest_phone,
          mssql_col_room_number: cols.room_number || prev.mssql_col_room_number,
          mssql_col_checkin: cols.checkin || prev.mssql_col_checkin,
          mssql_col_checkout: cols.checkout || prev.mssql_col_checkout,
          mssql_col_status: cols.status || prev.mssql_col_status,
          mssql_col_status_confirmed: r.data.active_statuses || prev.mssql_col_status_confirmed,
        }))
        setShowAdvanced(true)
      }
    } catch (e) {
      setDetectResult({ success: false, error: e.response?.data?.detail || 'Detection failed' })
    } finally { setDetecting(false) }
  }

  const f = (k, v) => setForm(p => ({ ...p, [k]: v }))
  const inp = (k, label, type = 'text', ph = '') => (
    <div>
      <label className="text-xs text-slate-400 mb-1 block">{label}</label>
      <input type={type} value={form[k] || ''} onChange={e => f(k, type === 'number' ? +e.target.value : e.target.value)}
        placeholder={ph} className="w-full bg-dark-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" />
    </div>
  )

  const StatusBadge = ({ k }) => {
    const v = testResult[k]
    if (!v) return null
    if (v === 'loading') return <Loader className="w-4 h-4 animate-spin text-yellow-400" />
    if (v === 'ok') return <CheckCircle className="w-4 h-4 text-green-400" />
    return <span className="text-xs text-red-400">{v.replace('fail_', '')}</span>
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Hotels</h1>
          <p className="text-slate-400 text-sm mt-1">Configure PMS and Mikrotik connections</p>
        </div>
        <button onClick={() => { setShowForm(true); setEditing(null); setForm(DEFAULT); setDetectResult(null) }}
          className="flex items-center gap-2 bg-brand-600 hover:bg-brand-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
          <Plus className="w-4 h-4" /> Add Hotel
        </button>
      </div>

      {/* Hotel Cards */}
      <div className="space-y-4">
        {hotels.map(h => (
          <div key={h.id} className="card p-5">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-white font-semibold text-lg">{h.name}</h3>
                <p className="text-slate-400 text-sm">Code: <span className="text-brand-400 font-mono">{h.hotspot_code || '—'}</span></p>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => testMssql(h.id)} className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors">
                  <Database className="w-3.5 h-3.5" /> Test PMS <StatusBadge k={`mssql_${h.id}`} />
                </button>
                <button onClick={() => testMikrotik(h.id)} className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors">
                  <Router className="w-3.5 h-3.5" /> Test Mikrotik <StatusBadge k={`mk_${h.id}`} />
                </button>
                <button onClick={() => { setEditing(h.id); setForm(h); setShowForm(true); setDetectResult(null); setShowAdvanced(false) }}
                  className="p-2 bg-slate-800 hover:bg-brand-600 text-slate-400 hover:text-white rounded-lg transition-colors">
                  <Edit2 className="w-4 h-4" />
                </button>
                <button onClick={() => del(h.id)} className="p-2 bg-slate-800 hover:bg-red-600 text-slate-400 hover:text-white rounded-lg transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-3 text-xs text-slate-500">
              <span>PMS: {h.mssql_server || '—'} / {h.mssql_database || '—'}</span>
              <span>Table: <span className="font-mono text-slate-400">{h.mssql_table_booking}</span></span>
              <span>Mikrotik: {h.mikrotik_host || '—'}</span>
            </div>
          </div>
        ))}
        {hotels.length === 0 && (
          <div className="text-center py-16 text-slate-500">
            <Wifi className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No hotels configured yet</p>
          </div>
        )}
      </div>

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-dark-800 border border-slate-700 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-dark-800 border-b border-slate-700 px-6 py-4 flex items-center justify-between rounded-t-2xl">
              <h2 className="text-lg font-bold text-white">{editing ? 'Edit Hotel' : 'Add Hotel'}</h2>
              <button onClick={() => { setShowForm(false); setDetectResult(null) }} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Basic */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2"><Wifi className="w-4 h-4 text-brand-400" /> Basic Info</h3>
                <div className="grid grid-cols-2 gap-3">
                  {inp('name', 'Hotel Name', 'text', 'Dubai Hotel')}
                  {inp('hotspot_code', 'Hotspot Code', 'text', 'dubaiHotel')}
                </div>
              </div>

              {/* MSSQL */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2"><Database className="w-4 h-4 text-blue-400" /> PMS Database (MSSQL)</h3>
                <div className="grid grid-cols-2 gap-3">
                  {inp('mssql_server', 'Server IP / Hostname', 'text', '192.168.1.10')}
                  {inp('mssql_port', 'Port', 'number', '1433')}
                  {inp('mssql_database', 'Database Name', 'text', 'NEXT70')}
                  {inp('mssql_username', 'Username', 'text', 'sa')}
                </div>
                {inp('mssql_password', 'Password', 'password')}

                {/* Auto-detect button — only show when editing */}
                {editing && (
                  <div className="pt-1">
                    <button onClick={autoDetect} disabled={detecting}
                      className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-purple-600 to-brand-600 hover:from-purple-500 hover:to-brand-500 text-white py-2.5 rounded-lg text-sm font-medium transition-all disabled:opacity-60">
                      {detecting ? <><Loader className="w-4 h-4 animate-spin" /> Scanning database...</> : <><Zap className="w-4 h-4" /> Auto-Detect Table & Columns</>}
                    </button>

                    {detectResult && (
                      <div className={`mt-3 p-3 rounded-lg border text-sm ${detectResult.success ? 'bg-green-500/10 border-green-500/30 text-green-300' : 'bg-red-500/10 border-red-500/30 text-red-300'}`}>
                        <div className="flex items-center gap-2 font-medium mb-1">
                          {detectResult.success ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                          {detectResult.success ? 'Auto-detected & applied!' : 'Could not auto-detect'}
                        </div>
                        {detectResult.message && <p className="text-xs opacity-80">{detectResult.message}</p>}
                        {detectResult.error && <p className="text-xs opacity-80">{detectResult.error}</p>}
                        {detectResult.all_tables && !detectResult.success && (
                          <div className="mt-2">
                            <p className="text-xs mb-1 opacity-70">Found tables — select manually:</p>
                            <select onChange={e => f('mssql_table_booking', e.target.value)} value={form.mssql_table_booking}
                              className="w-full bg-dark-900 border border-slate-600 rounded px-2 py-1 text-xs text-white">
                              {detectResult.all_tables.map(t => <option key={t}>{t}</option>)}
                            </select>
                          </div>
                        )}
                        {detectResult.status_values?.length > 0 && (
                          <div className="mt-2 text-xs opacity-70">
                            Status values found: <span className="font-mono">{detectResult.status_values.join(', ')}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
                {!editing && (
                  <p className="text-xs text-slate-500 flex items-center gap-1">
                    <Zap className="w-3 h-3" /> Save hotel first, then use Auto-Detect to scan your database
                  </p>
                )}
              </div>

              {/* Advanced column mapping */}
              <div>
                <button onClick={() => setShowAdvanced(p => !p)}
                  className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors w-full">
                  {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  Advanced: Column Mapping
                  <span className="text-xs text-slate-600 ml-1">(auto-filled by detector)</span>
                </button>
                {showAdvanced && (
                  <div className="mt-3 space-y-3 p-4 bg-dark-900 rounded-lg border border-slate-800">
                    {inp('mssql_table_booking', 'Booking Table', 'text', 'PMS.RRVDATBL')}
                    <div className="grid grid-cols-2 gap-3">
                      {inp('mssql_col_booking_id', 'Booking ID Column')}
                      {inp('mssql_col_guest_name', 'Guest Name Column')}
                      {inp('mssql_col_guest_phone', 'Phone Column')}
                      {inp('mssql_col_room_number', 'Room Number Column')}
                      {inp('mssql_col_checkin', 'Check-in Column')}
                      {inp('mssql_col_checkout', 'Check-out Column')}
                      {inp('mssql_col_status', 'Status Column')}
                      {inp('mssql_col_status_confirmed', 'Active Statuses (comma)', 'text', 'R,I')}
                    </div>
                  </div>
                )}
              </div>

              {/* Mikrotik */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2"><Router className="w-4 h-4 text-green-400" /> Mikrotik Router</h3>
                <div className="grid grid-cols-2 gap-3">
                  {inp('mikrotik_host', 'Router IP', 'text', '192.168.88.1')}
                  {inp('mikrotik_port', 'API Port', 'number', '8728')}
                  {inp('mikrotik_username', 'Username', 'text', 'admin')}
                  {inp('mikrotik_password', 'Password', 'password')}
                  {inp('mikrotik_hotspot_server', 'Hotspot Server Name', 'text', 'hotspot1')}
                  {inp('hotspot_password_length', 'Password Length', 'number', '8')}
                </div>
                {inp('checkout_grace_minutes', 'Delete user after checkout (minutes)', 'number', '60')}
              </div>
            </div>

            <div className="sticky bottom-0 bg-dark-800 border-t border-slate-700 px-6 py-4 flex gap-3 rounded-b-2xl">
              <button onClick={save} disabled={loading}
                className="flex-1 flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-500 text-white py-2.5 rounded-lg font-medium transition-colors disabled:opacity-50">
                <Save className="w-4 h-4" /> {loading ? 'Saving...' : 'Save Hotel'}
              </button>
              <button onClick={() => { setShowForm(false); setDetectResult(null) }}
                className="px-6 bg-slate-700 hover:bg-slate-600 text-white py-2.5 rounded-lg transition-colors">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
