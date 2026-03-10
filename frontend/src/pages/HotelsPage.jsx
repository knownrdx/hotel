import { useEffect, useState } from 'react'
import api from '../lib/api'
import {
  Plus, Pencil, Trash2, TestTube, CheckCircle, XCircle,
  ChevronDown, ChevronUp, RefreshCw, Wifi, Database
} from 'lucide-react'

const defaultForm = {
  name: '', address: '',
  mssql_host: '', mssql_port: 1433, mssql_database: '', mssql_username: '', mssql_password: '',
  mssql_table_booking: 'Bookings', mssql_col_booking_id: 'BookingID',
  mssql_col_guest_name: 'GuestName', mssql_col_guest_phone: 'Phone',
  mssql_col_room_number: 'RoomNumber', mssql_col_checkin: 'CheckInDate',
  mssql_col_checkout: 'CheckOutDate', mssql_col_status: 'Status',
  mssql_col_status_confirmed: 'Confirmed',
  mikrotik_host: '', mikrotik_port: 8728, mikrotik_username: 'admin', mikrotik_password: '',
  mikrotik_hotspot_server: 'hotspot1', mikrotik_hotspot_profile: 'default',
  radius_host: '', radius_port: 1812, radius_secret: '', use_radius: false,
  sync_interval_minutes: 5, checkout_grace_minutes: 0, auto_sync_enabled: true,
}

function InputField({ label, name, value, onChange, type = 'text', placeholder = '' }) {
  return (
    <div>
      <label className="text-xs text-slate-400 font-medium block mb-1">{label}</label>
      <input
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full bg-dark-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-500 transition-colors"
      />
    </div>
  )
}

export default function HotelsPage() {
  const [hotels, setHotels] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(defaultForm)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState({})
  const [testResults, setTestResults] = useState({})
  const [syncing, setSyncing] = useState({})
  const [expandedSection, setExpandedSection] = useState('basic')

  const fetchHotels = async () => {
    try {
      const res = await api.get('/hotels/')
      setHotels(res.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchHotels() }, [])

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleEdit = (hotel) => {
    setEditingId(hotel.id)
    setForm({ ...defaultForm, ...hotel })
    setShowForm(true)
    setExpandedSection('basic')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editingId) {
        await api.put(`/hotels/${editingId}`, form)
      } else {
        await api.post('/hotels/', form)
      }
      await fetchHotels()
      setShowForm(false)
      setEditingId(null)
      setForm(defaultForm)
    } catch (err) {
      alert(err.response?.data?.detail || 'Error saving hotel')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Deactivate this hotel?')) return
    await api.delete(`/hotels/${id}`)
    fetchHotels()
  }

  const handleTestMSSQL = async (id) => {
    setTesting(t => ({ ...t, [`mssql_${id}`]: true }))
    const res = await api.post(`/hotels/${id}/test-mssql`)
    setTestResults(r => ({ ...r, [`mssql_${id}`]: res.data }))
    setTesting(t => ({ ...t, [`mssql_${id}`]: false }))
  }

  const handleTestMikrotik = async (id) => {
    setTesting(t => ({ ...t, [`mt_${id}`]: true }))
    const res = await api.post(`/hotels/${id}/test-mikrotik`)
    setTestResults(r => ({ ...r, [`mt_${id}`]: res.data }))
    setTesting(t => ({ ...t, [`mt_${id}`]: false }))
  }

  const handleSync = async (id) => {
    setSyncing(s => ({ ...s, [id]: true }))
    await api.post(`/sync/${id}`)
    setSyncing(s => ({ ...s, [id]: false }))
  }

  const Section = ({ id, title, children }) => (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setExpandedSection(expandedSection === id ? null : id)}
        className="w-full flex items-center justify-between px-4 py-3 bg-slate-800/50 text-sm font-medium text-white hover:bg-slate-800"
      >
        {title}
        {expandedSection === id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>
      {expandedSection === id && (
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-3">{children}</div>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Hotels</h1>
          <p className="text-slate-400 text-sm mt-0.5">Manage hotel connections & Mikrotik settings</p>
        </div>
        <button
          onClick={() => { setShowForm(true); setEditingId(null); setForm(defaultForm) }}
          className="flex items-center gap-2 bg-brand-600 hover:bg-brand-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Hotel
        </button>
      </div>

      {/* Hotel list */}
      <div className="space-y-3">
        {loading ? (
          <div className="card p-8 text-center text-slate-500">Loading...</div>
        ) : hotels.length === 0 ? (
          <div className="card p-12 text-center">
            <Wifi className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400">No hotels added yet</p>
            <p className="text-slate-600 text-sm mt-1">Click "Add Hotel" to get started</p>
          </div>
        ) : (
          hotels.map(hotel => (
            <div key={hotel.id} className="card p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-white">{hotel.name}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${hotel.is_active ? 'badge-active' : 'badge-deleted'}`}>
                      {hotel.is_active ? 'Active' : 'Inactive'}
                    </span>
                    {hotel.auto_sync_enabled && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
                        Auto-sync {hotel.sync_interval_minutes}m
                      </span>
                    )}
                  </div>
                  {hotel.address && <p className="text-slate-400 text-sm mt-0.5">{hotel.address}</p>}
                  <div className="flex flex-wrap gap-3 mt-2 text-xs text-slate-500 font-mono">
                    {hotel.mssql_host && <span className="flex items-center gap-1"><Database className="w-3 h-3" />{hotel.mssql_host}/{hotel.mssql_database}</span>}
                    {hotel.mikrotik_host && <span className="flex items-center gap-1"><Wifi className="w-3 h-3" />{hotel.mikrotik_host}:{hotel.mikrotik_port}</span>}
                  </div>
                  {/* Test results */}
                  {testResults[`mssql_${hotel.id}`] && (
                    <div className={`mt-2 text-xs flex items-center gap-1 ${testResults[`mssql_${hotel.id}`].success ? 'text-emerald-400' : 'text-red-400'}`}>
                      {testResults[`mssql_${hotel.id}`].success ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                      MSSQL: {testResults[`mssql_${hotel.id}`].message}
                    </div>
                  )}
                  {testResults[`mt_${hotel.id}`] && (
                    <div className={`mt-1 text-xs flex items-center gap-1 ${testResults[`mt_${hotel.id}`].success ? 'text-emerald-400' : 'text-red-400'}`}>
                      {testResults[`mt_${hotel.id}`].success ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                      Mikrotik: {testResults[`mt_${hotel.id}`].message}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button onClick={() => handleTestMSSQL(hotel.id)} disabled={testing[`mssql_${hotel.id}`]} className="p-2 text-slate-400 hover:text-brand-400 hover:bg-slate-800 rounded-lg transition-colors" title="Test MSSQL">
                    {testing[`mssql_${hotel.id}`] ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
                  </button>
                  <button onClick={() => handleTestMikrotik(hotel.id)} disabled={testing[`mt_${hotel.id}`]} className="p-2 text-slate-400 hover:text-brand-400 hover:bg-slate-800 rounded-lg transition-colors" title="Test Mikrotik">
                    {testing[`mt_${hotel.id}`] ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Wifi className="w-4 h-4" />}
                  </button>
                  <button onClick={() => handleSync(hotel.id)} disabled={syncing[hotel.id]} className="p-2 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded-lg transition-colors" title="Sync now">
                    <RefreshCw className={`w-4 h-4 ${syncing[hotel.id] ? 'animate-spin text-emerald-400' : ''}`} />
                  </button>
                  <button onClick={() => handleEdit(hotel)} className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors">
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button onClick={() => handleDelete(hotel.id)} className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Form Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-10 bg-black/70 overflow-y-auto">
          <div className="w-full max-w-2xl card mb-10">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
              <h2 className="font-semibold text-white">{editingId ? 'Edit Hotel' : 'Add New Hotel'}</h2>
              <button onClick={() => { setShowForm(false); setEditingId(null) }} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <Section id="basic" title="Basic Information">
                <div className="md:col-span-2">
                  <InputField label="Hotel Name *" name="name" value={form.name} onChange={handleChange} placeholder="Grand Hotel" />
                </div>
                <div className="md:col-span-2">
                  <InputField label="Address" name="address" value={form.address} onChange={handleChange} placeholder="123 Main St" />
                </div>
              </Section>

              <Section id="mssql" title="🗄️ MSSQL Database Connection">
                <InputField label="Host/IP" name="mssql_host" value={form.mssql_host} onChange={handleChange} placeholder="192.168.1.100" />
                <InputField label="Port" name="mssql_port" value={form.mssql_port} onChange={handleChange} type="number" />
                <InputField label="Database Name" name="mssql_database" value={form.mssql_database} onChange={handleChange} placeholder="HotelDB" />
                <InputField label="Username" name="mssql_username" value={form.mssql_username} onChange={handleChange} placeholder="sa" />
                <InputField label="Password" name="mssql_password" value={form.mssql_password} onChange={handleChange} type="password" />
                <InputField label="Booking Table Name" name="mssql_table_booking" value={form.mssql_table_booking} onChange={handleChange} />
                <InputField label="Column: Booking ID" name="mssql_col_booking_id" value={form.mssql_col_booking_id} onChange={handleChange} />
                <InputField label="Column: Guest Name" name="mssql_col_guest_name" value={form.mssql_col_guest_name} onChange={handleChange} />
                <InputField label="Column: Phone" name="mssql_col_guest_phone" value={form.mssql_col_guest_phone} onChange={handleChange} />
                <InputField label="Column: Room Number" name="mssql_col_room_number" value={form.mssql_col_room_number} onChange={handleChange} />
                <InputField label="Column: Check-In Date" name="mssql_col_checkin" value={form.mssql_col_checkin} onChange={handleChange} />
                <InputField label="Column: Check-Out Date" name="mssql_col_checkout" value={form.mssql_col_checkout} onChange={handleChange} />
                <InputField label="Column: Status" name="mssql_col_status" value={form.mssql_col_status} onChange={handleChange} />
                <InputField label="Status value for Confirmed" name="mssql_col_status_confirmed" value={form.mssql_col_status_confirmed} onChange={handleChange} placeholder="Confirmed" />
              </Section>

              <Section id="mikrotik" title="📡 Mikrotik Hotspot">
                <InputField label="Router IP" name="mikrotik_host" value={form.mikrotik_host} onChange={handleChange} placeholder="192.168.88.1" />
                <InputField label="API Port" name="mikrotik_port" value={form.mikrotik_port} onChange={handleChange} type="number" />
                <InputField label="Username" name="mikrotik_username" value={form.mikrotik_username} onChange={handleChange} placeholder="admin" />
                <InputField label="Password" name="mikrotik_password" value={form.mikrotik_password} onChange={handleChange} type="password" />
                <InputField label="Hotspot Server Name" name="mikrotik_hotspot_server" value={form.mikrotik_hotspot_server} onChange={handleChange} placeholder="hotspot1" />
                <InputField label="Default Profile" name="mikrotik_hotspot_profile" value={form.mikrotik_hotspot_profile} onChange={handleChange} placeholder="default" />
              </Section>

              <Section id="radius" title="🔐 RADIUS (Optional)">
                <div className="md:col-span-2 flex items-center gap-3">
                  <input type="checkbox" name="use_radius" checked={form.use_radius} onChange={handleChange} id="use_radius" className="w-4 h-4 accent-brand-500" />
                  <label htmlFor="use_radius" className="text-sm text-slate-300">Enable RADIUS integration</label>
                </div>
                <InputField label="RADIUS Host" name="radius_host" value={form.radius_host} onChange={handleChange} />
                <InputField label="RADIUS Port" name="radius_port" value={form.radius_port} onChange={handleChange} type="number" />
                <InputField label="Shared Secret" name="radius_secret" value={form.radius_secret} onChange={handleChange} type="password" />
              </Section>

              <Section id="sync" title="⚙️ Sync Settings">
                <InputField label="Sync Interval (minutes)" name="sync_interval_minutes" value={form.sync_interval_minutes} onChange={handleChange} type="number" />
                <InputField label="Checkout Grace Period (minutes)" name="checkout_grace_minutes" value={form.checkout_grace_minutes} onChange={handleChange} type="number" />
                <div className="md:col-span-2 flex items-center gap-3">
                  <input type="checkbox" name="auto_sync_enabled" checked={form.auto_sync_enabled} onChange={handleChange} id="auto_sync" className="w-4 h-4 accent-brand-500" />
                  <label htmlFor="auto_sync" className="text-sm text-slate-300">Enable automatic sync</label>
                </div>
              </Section>

              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={saving} className="flex-1 bg-brand-600 hover:bg-brand-500 text-white py-2.5 rounded-lg font-medium text-sm transition-colors disabled:opacity-50">
                  {saving ? 'Saving...' : editingId ? 'Save Changes' : 'Add Hotel'}
                </button>
                <button type="button" onClick={() => { setShowForm(false); setEditingId(null) }} className="px-6 bg-slate-800 hover:bg-slate-700 text-white py-2.5 rounded-lg font-medium text-sm transition-colors">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
