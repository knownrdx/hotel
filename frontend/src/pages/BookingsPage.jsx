import { useEffect, useState } from 'react'
import api from '../lib/api'
import { RefreshCw, Search, CalendarDays, User, Phone, Hash } from 'lucide-react'
import { format, parseISO, isValid } from 'date-fns'

function formatDate(val) {
  if (!val) return '—'
  try {
    const d = parseISO(val)
    return isValid(d) ? format(d, 'dd MMM yyyy HH:mm') : val
  } catch { return val }
}

export default function BookingsPage() {
  const [bookings, setBookings] = useState([])
  const [hotels, setHotels] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedHotel, setSelectedHotel] = useState('')
  const [search, setSearch] = useState('')
  const [mode, setMode] = useState('live') // 'live' | 'local'

  const fetchHotels = async () => {
    const res = await api.get('/hotels/')
    setHotels(res.data)
  }

  const fetchBookings = async () => {
    setLoading(true)
    try {
      const endpoint = mode === 'live' ? '/bookings/live' : '/bookings'
      const params = selectedHotel ? { hotel_id: selectedHotel } : {}
      const res = await api.get(endpoint, { params })
      setBookings(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchHotels() }, [])
  useEffect(() => { fetchBookings() }, [selectedHotel, mode])

  const filtered = bookings.filter(b => {
    if (!search) return true
    const s = search.toLowerCase()
    return (
      String(b.guest_name || '').toLowerCase().includes(s) ||
      String(b.room_number || '').toLowerCase().includes(s) ||
      String(b.booking_id || b.external_booking_id || '').toLowerCase().includes(s)
    )
  })

  const getStatusColor = (status) => {
    if (!status) return 'text-slate-400'
    const s = status.toLowerCase()
    if (s.includes('confirm') || s.includes('check')) return 'text-emerald-400'
    if (s.includes('cancel')) return 'text-red-400'
    return 'text-yellow-400'
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Bookings</h1>
          <p className="text-slate-400 text-sm mt-0.5">Hotel booking data from MSSQL databases</p>
        </div>
        <button onClick={fetchBookings} disabled={loading} className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white px-3 py-2 rounded-lg text-sm transition-colors">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="flex bg-slate-800 rounded-lg p-1 gap-1">
          <button onClick={() => setMode('live')} className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${mode === 'live' ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white'}`}>
            🔴 Live (MSSQL)
          </button>
          <button onClick={() => setMode('local')} className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${mode === 'local' ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white'}`}>
            💾 Synced (Local)
          </button>
        </div>
        <select
          value={selectedHotel}
          onChange={e => setSelectedHotel(e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
        >
          <option value="">All Hotels</option>
          {hotels.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search guest, room, booking ID..."
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs text-slate-500 uppercase tracking-wider">
                <th className="text-left px-4 py-3 font-semibold">Hotel</th>
                <th className="text-left px-4 py-3 font-semibold">Booking ID</th>
                <th className="text-left px-4 py-3 font-semibold">Guest</th>
                <th className="text-left px-4 py-3 font-semibold">Room</th>
                <th className="text-left px-4 py-3 font-semibold">Check-In</th>
                <th className="text-left px-4 py-3 font-semibold">Check-Out</th>
                <th className="text-left px-4 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-500">Loading...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-500">No bookings found</td></tr>
              ) : (
                filtered.map((b, i) => (
                  <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 text-slate-300">{b.hotel_name || `Hotel #${b.hotel_id}`}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{b.booking_id || b.external_booking_id || '—'}</td>
                    <td className="px-4 py-3">
                      <div className="text-white font-medium">{b.guest_name || '—'}</div>
                      {b.guest_phone && <div className="text-xs text-slate-500 mt-0.5">{b.guest_phone}</div>}
                    </td>
                    <td className="px-4 py-3 font-mono text-brand-400">{b.room_number || '—'}</td>
                    <td className="px-4 py-3 text-slate-300 text-xs">{formatDate(b.check_in)}</td>
                    <td className="px-4 py-3 text-slate-300 text-xs">{formatDate(b.check_out)}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium ${getStatusColor(b.status)}`}>{b.status || '—'}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {!loading && <div className="px-4 py-3 border-t border-slate-800 text-xs text-slate-500">{filtered.length} bookings shown</div>}
      </div>
    </div>
  )
}
