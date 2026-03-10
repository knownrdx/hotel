import { useEffect, useState } from 'react'
import api from '../lib/api'
import { Hotel, Wifi, CalendarDays, RefreshCw, CheckCircle, XCircle, Clock, TrendingUp } from 'lucide-react'
import { format, parseISO } from 'date-fns'

function StatCard({ icon: Icon, label, value, color = 'blue', loading }) {
  const colors = {
    blue: 'bg-brand-600/15 text-brand-400 border-brand-500/20',
    green: 'bg-emerald-600/15 text-emerald-400 border-emerald-500/20',
    purple: 'bg-purple-600/15 text-purple-400 border-purple-500/20',
    orange: 'bg-orange-600/15 text-orange-400 border-orange-500/20',
  }
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl border flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        {loading && <div className="w-4 h-4 border-2 border-slate-700 border-t-brand-400 rounded-full animate-spin" />}
      </div>
      <div className="text-2xl font-bold text-white font-mono">{loading ? '—' : value}</div>
      <div className="text-xs text-slate-400 mt-1 font-medium">{label}</div>
    </div>
  )
}

function StatusBadge({ status }) {
  if (status === 'success') return <span className="badge-success inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full"><CheckCircle className="w-3 h-3" />Success</span>
  if (status === 'failed') return <span className="badge-failed inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full"><XCircle className="w-3 h-3" />Failed</span>
  return <span className="badge-pending inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full"><Clock className="w-3 h-3" />Pending</span>
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)

  const fetchStats = async () => {
    try {
      const res = await api.get('/dashboard/stats')
      setStats(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 30000) // refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const handleSyncAll = async () => {
    setSyncing(true)
    try {
      await api.post('/sync/all')
      await fetchStats()
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 text-sm mt-0.5">Live overview of all hotels & hotspot activity</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
            <span className="live-dot w-2 h-2 rounded-full bg-emerald-400 block" />
            Live
          </div>
          <button
            onClick={handleSyncAll}
            disabled={syncing}
            className="flex items-center gap-2 bg-brand-600 hover:bg-brand-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
            Sync All
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Hotel} label="Active Hotels" value={stats?.total_hotels} color="blue" loading={loading} />
        <StatCard icon={CalendarDays} label="Total Bookings" value={stats?.total_bookings} color="purple" loading={loading} />
        <StatCard icon={Wifi} label="Active Hotspot Users" value={stats?.active_hotspot_users} color="green" loading={loading} />
        <StatCard icon={TrendingUp} label="Total Syncs" value={stats?.total_syncs} color="orange" loading={loading} />
      </div>

      {/* Recent Logs */}
      <div className="card">
        <div className="px-5 py-4 border-b border-slate-800">
          <h2 className="font-semibold text-white">Recent Sync Activity</h2>
        </div>
        <div className="divide-y divide-slate-800">
          {loading ? (
            <div className="px-5 py-8 text-center text-slate-500 text-sm">Loading...</div>
          ) : stats?.recent_logs?.length === 0 ? (
            <div className="px-5 py-8 text-center text-slate-500 text-sm">No sync activity yet</div>
          ) : (
            stats?.recent_logs?.map(log => (
              <div key={log.id} className="px-5 py-3 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <StatusBadge status={log.status} />
                  <span className="text-sm text-slate-300 truncate">{log.message || 'Sync completed'}</span>
                </div>
                <div className="flex items-center gap-4 flex-shrink-0 text-xs text-slate-500 font-mono">
                  <span className="text-emerald-400">+{log.users_created}</span>
                  <span className="text-red-400">-{log.users_deleted}</span>
                  <span>{log.created_at ? format(parseISO(log.created_at), 'HH:mm:ss') : ''}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
