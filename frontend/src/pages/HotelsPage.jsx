import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Plus, Edit2, Trash2, Wifi, Database, Router, Save, X, Zap, CheckCircle, AlertCircle, Loader, ChevronDown, ChevronUp, Table, Eye, Search } from 'lucide-react'

const DEFAULT = {
  name: '', hotspot_code: '',
  mssql_server: '', mssql_port: 1433, mssql_database: '', mssql_username: '', mssql_password: '',
  mssql_table_booking: '',
  mssql_col_booking_id: '', mssql_col_guest_name: '', mssql_col_guest_phone: '',
  mssql_col_room_number: '', mssql_col_checkin: '', mssql_col_checkout: '',
  mssql_col_status: '', mssql_col_status_confirmed: '',
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

  // Table Browser state
  const [showBrowser, setShowBrowser] = useState(false)
  const [allTables, setAllTables] = useState([])
  const [scanLoading, setScanLoading] = useState(false)
  const [selectedTable, setSelectedTable] = useState(null)
  const [tableColumns, setTableColumns] = useState([])
  const [tableSample, setTableSample] = useState([])
  const [sampleLoading, setSampleLoading] = useState(false)
  const [tableSearch, setTableSearch] = useState('')
  const [colMapping, setColMapping] = useState({})

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

  // ===== TABLE BROWSER =====
  const openBrowser = async () => {
    if (!editing) return
    setShowBrowser(true)
    setScanLoading(true)
    setSelectedTable(null)
    setTableColumns([])
    setTableSample([])
    setColMapping({})
    setTableSearch('')
    try {
      const r = await api.get(`/hotels/${editing}/mssql-scan-all`)
      setAllTables(r.data.tables || [])
    } catch (e) {
      alert('Failed to scan: ' + (e.response?.data?.detail || e.message))
    } finally { setScanLoading(false) }
  }

  const viewTable = async (tableName) => {
    setSelectedTable(tableName)
    setSampleLoading(true)
    setColMapping({})
    try {
      const [colRes, sampleRes] = await Promise.all([
        api.get(`/hotels/${editing}/mssql-columns/${tableName}`),
        api.get(`/hotels/${editing}/mssql-sample/${tableName}`)
      ])
      setTableColumns(colRes.data.columns || [])
      setTableSample(sampleRes.data.sample || [])
    } catch (e) {
      alert('Failed to load table: ' + (e.response?.data?.detail || e.message))
    } finally { setSampleLoading(false) }
  }

  const applyMapping = () => {
    setForm(prev => ({
      ...prev,
      mssql_table_booking: selectedTable || prev.mssql_table_booking,
      mssql_col_booking_id: colMapping.booking_id || prev.mssql_col_booking_id,
      mssql_col_guest_name: colMapping.guest_name || prev.mssql_col_guest_name,
      mssql_col_guest_phone: colMapping.guest_phone || prev.mssql_col_guest_phone,
      mssql_col_room_number: colMapping.room_number || prev.mssql_col_room_number,
      mssql_col_checkin: colMapping.checkin || prev.mssql_col_checkin,
      mssql_col_checkout: colMapping.checkout || prev.mssql_col_checkout,
      mssql_col_status: colMapping.status || prev.mssql_col_status,
      mssql_col_status_confirmed: colMapping.status_values || prev.mssql_col_status_confirmed,
    }))
    setShowBrowser(false)
    setShowAdvanced(true)
  }

  const MAPPING_FIELDS = [
    { key: 'booking_id', label: 'Booking ID', color: 'text-blue-400' },
    { key: 'guest_name', label: 'Guest Name', color: 'text-emerald-400' },
    { key: 'guest_phone', label: 'Phone', color: 'text-cyan-400' },
    { key: 'room_number', label: 'Room No', color: 'text-yellow-400' },
    { key: 'checkin', label: 'Check-in', color: 'text-purple-400' },
    { key: 'checkout', label: 'Check-out', color: 'text-pink-400' },
    { key: 'status', label: 'Status', color: 'text-orange-400' },
  ]

  const assignColumn = (colName, fieldKey) => {
    setColMapping(prev => {
      const next = { ...prev }
      Object.keys(next).forEach(k => { if (next[k] === colName && k !== fieldKey) delete next[k] })
      Object.keys(next).forEach(k => { if (k === fieldKey) delete next[k] })
      if (colName) next[fieldKey] = colName
      return next
    })
  }

  const getFieldForColumn = (colName) => {
    const entry = Object.entries(colMapping).find(([k, v]) => v === colName)
    return entry ? entry[0] : null
  }

  const filteredTables = allTables.filter(t => {
    if (!tableSearch) return true
    return t.table.toLowerCase().includes(tableSearch.toLowerCase()) ||
      t.columns.some(c => c.toLowerCase().includes(tableSearch.toLowerCase()))
  })

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
              <span>Table: <span className="font-mono text-slate-400">{h.mssql_table_booking || '—'}</span></span>
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
            <div className="sticky top-0 bg-dark-800 border-b border-slate-700 px-6 py-4 flex items-center justify-between rounded-t-2xl z-10">
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

                {editing && (
                  <div className="pt-1 space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <button onClick={autoDetect} disabled={detecting}
                        className="flex items-center justify-center gap-2 bg-gradient-to-r from-purple-600 to-brand-600 hover:from-purple-500 hover:to-brand-500 text-white py-2.5 rounded-lg text-sm font-medium transition-all disabled:opacity-60">
                        {detecting ? <><Loader className="w-4 h-4 animate-spin" /> Scanning...</> : <><Zap className="w-4 h-4" /> Auto-Detect</>}
                      </button>
                      <button onClick={openBrowser}
                        className="flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white py-2.5 rounded-lg text-sm font-medium transition-all">
                        <Table className="w-4 h-4" /> Browse Tables
                      </button>
                    </div>

                    {detectResult && (
                      <div className={`p-3 rounded-lg border text-sm ${detectResult.success ? 'bg-green-500/10 border-green-500/30 text-green-300' : 'bg-red-500/10 border-red-500/30 text-red-300'}`}>
                        <div className="flex items-center gap-2 font-medium mb-1">
                          {detectResult.success ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                          {detectResult.success ? 'Auto-detected & applied!' : 'Could not auto-detect — use Browse Tables instead'}
                        </div>
                        {detectResult.message && <p className="text-xs opacity-80">{detectResult.message}</p>}
                        {detectResult.error && <p className="text-xs opacity-80">{detectResult.error}</p>}
                      </div>
                    )}
                  </div>
                )}
                {!editing && (
                  <p className="text-xs text-slate-500 flex items-center gap-1">
                    <Zap className="w-3 h-3" /> Save hotel first, then use Auto-Detect or Browse Tables
                  </p>
                )}
              </div>

              {/* Advanced column mapping */}
              <div>
                <button onClick={() => setShowAdvanced(p => !p)}
                  className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors w-full">
                  {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  Column Mapping
                  {form.mssql_table_booking && <span className="text-xs text-emerald-400 ml-2">✓ {form.mssql_table_booking}</span>}
                </button>
                {showAdvanced && (
                  <div className="mt-3 space-y-3 p-4 bg-dark-900 rounded-lg border border-slate-800">
                    {inp('mssql_table_booking', 'Booking Table', 'text', 'schema.tablename')}
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

      {/* ===== TABLE BROWSER MODAL ===== */}
      {showBrowser && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[60] p-4">
          <div className="bg-dark-800 border border-slate-700 rounded-2xl w-full max-w-5xl max-h-[90vh] flex flex-col">
            <div className="border-b border-slate-700 px-6 py-4 flex items-center justify-between flex-shrink-0">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2"><Database className="w-5 h-5 text-blue-400" /> Table Browser</h2>
                <p className="text-xs text-slate-500 mt-0.5">Table select করুন → Sample data দেখুন → Column assign করুন → Apply</p>
              </div>
              <button onClick={() => setShowBrowser(false)} className="text-slate-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>

            <div className="flex-1 overflow-hidden flex">
              {/* Left panel: Table list */}
              <div className="w-72 border-r border-slate-700 flex flex-col flex-shrink-0">
                <div className="p-3 border-b border-slate-800">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                    <input value={tableSearch} onChange={e => setTableSearch(e.target.value)}
                      placeholder="Search tables..."
                      className="w-full bg-dark-900 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500" />
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {scanLoading ? (
                    <div className="flex items-center justify-center py-10 gap-2 text-slate-500 text-sm">
                      <Loader className="w-4 h-4 animate-spin" /> Scanning...
                    </div>
                  ) : filteredTables.length === 0 ? (
                    <div className="px-4 py-8 text-center text-slate-600 text-xs">No tables found</div>
                  ) : (
                    filteredTables.map(t => (
                      <button key={t.table} onClick={() => viewTable(t.table)}
                        className={`w-full text-left px-4 py-2.5 border-b border-slate-800/50 hover:bg-slate-800 transition-colors ${
                          selectedTable === t.table ? 'bg-brand-600/20 border-l-2 border-l-brand-400' : ''
                        }`}>
                        <div className="text-xs font-mono text-white truncate">{t.table}</div>
                        <div className="text-xs text-slate-500 mt-0.5">{t.column_count} columns</div>
                      </button>
                    ))
                  )}
                </div>
              </div>

              {/* Right panel: Table detail */}
              <div className="flex-1 flex flex-col overflow-hidden">
                {!selectedTable ? (
                  <div className="flex-1 flex items-center justify-center text-slate-600">
                    <div className="text-center">
                      <Table className="w-12 h-12 mx-auto mb-3 opacity-30" />
                      <p className="text-sm">বাম পাশ থেকে একটি table select করুন</p>
                    </div>
                  </div>
                ) : sampleLoading ? (
                  <div className="flex-1 flex items-center justify-center gap-2 text-slate-500">
                    <Loader className="w-4 h-4 animate-spin" /> Loading...
                  </div>
                ) : (
                  <>
                    {/* Column mapping */}
                    <div className="p-4 border-b border-slate-700 flex-shrink-0">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-semibold text-white">
                          <span className="font-mono text-brand-400">{selectedTable}</span>
                          <span className="text-slate-500 ml-2 font-normal">— {tableColumns.length} columns</span>
                        </h3>
                        <button onClick={applyMapping}
                          className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-1.5 rounded-lg text-xs font-medium transition-colors">
                          <CheckCircle className="w-3.5 h-3.5" /> Apply & Use This Table
                        </button>
                      </div>

                      <div className="grid grid-cols-4 gap-2">
                        {MAPPING_FIELDS.map(({ key, label, color }) => (
                          <div key={key}>
                            <label className={`text-xs font-medium mb-1 block ${color}`}>{label}</label>
                            <select
                              value={colMapping[key] || ''}
                              onChange={e => assignColumn(e.target.value, key)}
                              className="w-full bg-dark-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500">
                              <option value="">— select —</option>
                              {tableColumns.map(c => (
                                <option key={c.name} value={c.name}>{c.name} ({c.type})</option>
                              ))}
                            </select>
                          </div>
                        ))}
                        <div>
                          <label className="text-xs font-medium mb-1 block text-red-400">Active Statuses</label>
                          <input
                            value={colMapping.status_values || ''}
                            onChange={e => setColMapping(p => ({ ...p, status_values: e.target.value }))}
                            placeholder="R,I"
                            className="w-full bg-dark-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-brand-500"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Sample data */}
                    <div className="flex-1 overflow-auto">
                      <div className="p-3 text-xs text-slate-500 border-b border-slate-800 bg-dark-900/50">
                        Sample Data (top 5 rows) — data দেখে সঠিক column চিনুন
                      </div>
                      {tableSample.length === 0 ? (
                        <div className="p-6 text-center text-slate-600 text-sm">No data in this table</div>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="border-b border-slate-800">
                                {Object.keys(tableSample[0]).map(col => {
                                  const field = getFieldForColumn(col)
                                  const mf = field ? MAPPING_FIELDS.find(f => f.key === field) : null
                                  return (
                                    <th key={col} className={`text-left px-3 py-2 font-mono whitespace-nowrap ${
                                      mf ? mf.color + ' bg-slate-800/50' : 'text-slate-500'
                                    }`}>
                                      {col}
                                      {mf && <span className="block font-sans text-xs opacity-60">↑ {mf.label}</span>}
                                    </th>
                                  )
                                })}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/30">
                              {tableSample.map((row, i) => (
                                <tr key={i} className="hover:bg-slate-800/20">
                                  {Object.entries(row).map(([col, val]) => {
                                    const field = getFieldForColumn(col)
                                    const mf = field ? MAPPING_FIELDS.find(f => f.key === field) : null
                                    return (
                                      <td key={col} className={`px-3 py-2 whitespace-nowrap max-w-48 truncate ${
                                        mf ? 'text-white font-medium bg-slate-800/30' : 'text-slate-400'
                                      }`}>
                                        {val === null ? <span className="text-slate-700 italic">NULL</span> : String(val)}
                                      </td>
                                    )
                                  })}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
