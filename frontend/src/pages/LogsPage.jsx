import { useEffect, useState } from 'react'
import api from '../lib/api'
import { RefreshCw, CheckCircle, XCircle, Clock, ChevronDown, ChevronUp } from 'lucide-react'
import { format, parseISO } from 'date-fns'

export default function LogsPage() {
  const [logs, setLogs] = useState([])
  const [hotels, setHotels] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedHotel, setSelectedHotel] = useState('')
  const [expanded, setExpanded] = useState({})

  const fetchHotels = async () => {
    const res = await api.get('/hotels/')
    setHotels(res.data)
  }

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const params = { limit: 100 }
      if (selectedHotel) params.hotel_id = selectedHotel
      const res = await api.get('/logs', { params })
      setLogs(res.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchHotels(); }, [])
  useEffect(() => { fetchLogs() }, [selectedHotel])

  const getHotelName = (id) => hotels.find(h => h.id === id)?.name || `Hotel #${id}`

  const StatusIcon = ({ status }) => {
    if (status === 'success') return <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
    if (status === 'failed') return <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
    return <Clock className="w-4 h-4 text-yellow-400 flex-shrink-0" />
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Sync Logs</h1>
          <p className="text-slate-400 text-sm mt-0.5">History of all database sync operations</p>
        </div>
        <button onClick={fetchLogs} className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white px-3 py-2 rounded-lg text-sm transition-colors">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="flex gap-3">
        <select value={selectedHotel} onChange={e => setSelectedHotel(e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
          <option value="">All Hotels</option>
          {hotels.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
      </div>

      <div className="card overflow-hidden divide-y divide-slate-800">
        {loading ? (
          <div className="px-5 py-10 text-center text-slate-500">Loading...</div>
        ) : logs.length === 0 ? (
          <div className="px-5 py-10 text-center text-slate-500">No logs found</div>
        ) : (
          logs.map(log => (
            <div key={log.id}>
              <div
                className="flex items-center gap-4 px-5 py-3 hover:bg-slate-800/30 cursor-pointer transition-colors"
                onClick={() => setExpanded(e => ({ ...e, [log.id]: !e[log.id] }))}
              >
                <StatusIcon status={log.status} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-slate-300 truncate">{getHotelName(log.hotel_id)}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${
                      log.status === 'success' ? 'badge-success' :
                      log.status === 'failed' ? 'badge-failed' : 'badge-pending'
                    }`}>{log.status}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 truncate">{log.message}</p>
                </div>
                <div className="flex items-center gap-5 text-xs font-mono flex-shrink-0">
                  <span className="text-slate-400">📋 {log.bookings_found}</span>
                  <span className="text-emerald-400">+{log.users_created}</span>
                  <span className="text-red-400">-{log.users_deleted}</span>
                  <span className="text-slate-500">{log.created_at ? format(parseISO(log.created_at), 'dd MMM HH:mm:ss') : ''}</span>
                  {expanded[log.id] ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
                </div>
              </div>
              {expanded[log.id] && log.details && (
                <div className="px-5 pb-4 bg-slate-900/30">
                  <pre className="text-xs text-slate-400 font-mono bg-slate-900 rounded-lg p-3 overflow-x-auto">
                    {JSON.stringify(log.details, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
