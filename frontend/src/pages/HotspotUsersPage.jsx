import { useEffect, useState } from 'react'
import api from '../lib/api'
import { Plus, Trash2, RefreshCw, Search, Wifi, Copy, Check, Eye, EyeOff } from 'lucide-react'

export default function HotspotUsersPage() {
  const [users, setUsers] = useState([])
  const [hotels, setHotels] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedHotel, setSelectedHotel] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [deleting, setDeleting] = useState({})
  const [copied, setCopied] = useState({})
  const [showPasswords, setShowPasswords] = useState({})
  const [form, setForm] = useState({ hotel_id: '', username: '', password: '', profile: '', comment: '' })
  const [saving, setSaving] = useState(false)
  const [newUserResult, setNewUserResult] = useState(null)

  const fetchHotels = async () => {
    const res = await api.get('/hotels/')
    setHotels(res.data)
  }

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const params = {}
      if (selectedHotel) params.hotel_id = selectedHotel
      if (statusFilter) params.status = statusFilter
      params.limit = 100
      const res = await api.get('/hotspot-users', { params })
      setUsers(res.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchHotels() }, [])
  useEffect(() => { fetchUsers() }, [selectedHotel, statusFilter])

  const handleDelete = async (id) => {
    if (!confirm('Delete this hotspot user from Mikrotik?')) return
    setDeleting(d => ({ ...d, [id]: true }))
    await api.delete(`/hotspot-users/${id}`)
    await fetchUsers()
    setDeleting(d => ({ ...d, [id]: false }))
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const res = await api.post('/hotspot-users', {
        ...form,
        hotel_id: parseInt(form.hotel_id)
      })
      setNewUserResult(res.data)
      await fetchUsers()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error creating user')
    } finally {
      setSaving(false)
    }
  }

  const copyToClipboard = (text, key) => {
    navigator.clipboard.writeText(text)
    setCopied(c => ({ ...c, [key]: true }))
    setTimeout(() => setCopied(c => ({ ...c, [key]: false })), 2000)
  }

  const filtered = users.filter(u => {
    if (!search) return true
    const s = search.toLowerCase()
    return u.username.toLowerCase().includes(s)
  })

  const getHotelName = (id) => hotels.find(h => h.id === id)?.name || `Hotel #${id}`

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Hotspot Users</h1>
          <p className="text-slate-400 text-sm mt-0.5">Manage Mikrotik hotspot credentials</p>
        </div>
        <button
          onClick={() => { setShowForm(true); setNewUserResult(null) }}
          className="flex items-center gap-2 bg-brand-600 hover:bg-brand-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create User
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select value={selectedHotel} onChange={e => setSelectedHotel(e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
          <option value="">All Hotels</option>
          {hotels.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
        </select>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="deleted">Deleted</option>
          <option value="disabled">Disabled</option>
        </select>
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search username..."
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>
        <button onClick={fetchUsers} className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg transition-colors">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs text-slate-500 uppercase tracking-wider">
                <th className="text-left px-4 py-3">Username</th>
                <th className="text-left px-4 py-3">Password</th>
                <th className="text-left px-4 py-3">Hotel</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">Mikrotik</th>
                <th className="text-left px-4 py-3">Created</th>
                <th className="text-left px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-500">Loading...</td></tr>
              ) : filtered.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-10 text-center">
                  <Wifi className="w-10 h-10 text-slate-700 mx-auto mb-2" />
                  <p className="text-slate-500">No users found</p>
                </td></tr>
              ) : (
                filtered.map(u => (
                  <tr key={u.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-white">{u.username}</span>
                        <button onClick={() => copyToClipboard(u.username, `un_${u.id}`)} className="text-slate-600 hover:text-slate-400 transition-colors">
                          {copied[`un_${u.id}`] ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        </button>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">
                      <div className="flex items-center gap-2">
                        <span className="text-slate-400">
                          {showPasswords[u.id] ? (u.extra_info?.manual ? u.username : '••••••••') : '••••••••'}
                        </span>
                        <button onClick={() => setShowPasswords(p => ({ ...p, [u.id]: !p[u.id] }))} className="text-slate-600 hover:text-slate-400">
                          {showPasswords[u.id] ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                        </button>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{getHotelName(u.hotel_id)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block text-xs px-2 py-0.5 rounded-full border ${
                        u.status === 'active' ? 'badge-active' :
                        u.status === 'deleted' ? 'badge-deleted' : 'badge-disabled'
                      }`}>{u.status}</span>
                    </td>
                    <td className="px-4 py-3">
                      {u.mikrotik_created
                        ? <span className="text-emerald-400 text-xs">✓ Created</span>
                        : <span className="text-red-400 text-xs">✗ Failed</span>
                      }
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {u.created_at ? new Date(u.created_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {u.status === 'active' && (
                        <button onClick={() => handleDelete(u.id)} disabled={deleting[u.id]}
                          className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors">
                          {deleting[u.id] ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {!loading && <div className="px-4 py-3 border-t border-slate-800 text-xs text-slate-500">{filtered.length} users</div>}
      </div>

      {/* Create User Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70">
          <div className="w-full max-w-md card">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
              <h2 className="font-semibold text-white">Create Hotspot User</h2>
              <button onClick={() => { setShowForm(false); setNewUserResult(null) }} className="text-slate-400 hover:text-white">✕</button>
            </div>
            {newUserResult ? (
              <div className="p-6 space-y-4">
                <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-4">
                  <div className="text-emerald-400 font-semibold mb-3">✓ User Created Successfully!</div>
                  <div className="space-y-2 font-mono text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Username:</span>
                      <div className="flex items-center gap-2">
                        <span className="text-white">{newUserResult.username}</span>
                        <button onClick={() => copyToClipboard(newUserResult.username, 'new_un')} className="text-slate-500 hover:text-white">
                          {copied.new_un ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Password:</span>
                      <div className="flex items-center gap-2">
                        <span className="text-white">{newUserResult.password}</span>
                        <button onClick={() => copyToClipboard(newUserResult.password, 'new_pw')} className="text-slate-500 hover:text-white">
                          {copied.new_pw ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                <button onClick={() => { setShowForm(false); setNewUserResult(null) }} className="w-full bg-slate-800 hover:bg-slate-700 text-white py-2.5 rounded-lg text-sm font-medium transition-colors">
                  Close
                </button>
              </div>
            ) : (
              <form onSubmit={handleCreate} className="p-6 space-y-4">
                <div>
                  <label className="text-xs text-slate-400 font-medium block mb-1">Hotel *</label>
                  <select required value={form.hotel_id} onChange={e => setForm(f => ({ ...f, hotel_id: e.target.value }))}
                    className="w-full bg-dark-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
                    <option value="">Select Hotel</option>
                    {hotels.map(h => <option key={h.id} value={h.id}>{h.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-medium block mb-1">Username *</label>
                  <input required value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                    placeholder="room101_john"
                    className="w-full bg-dark-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-medium block mb-1">Password (leave blank to auto-generate)</label>
                  <input value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                    placeholder="Auto-generated"
                    className="w-full bg-dark-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-medium block mb-1">Profile (optional)</label>
                  <input value={form.profile} onChange={e => setForm(f => ({ ...f, profile: e.target.value }))}
                    placeholder="default"
                    className="w-full bg-dark-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-medium block mb-1">Comment</label>
                  <input value={form.comment} onChange={e => setForm(f => ({ ...f, comment: e.target.value }))}
                    placeholder="Guest note"
                    className="w-full bg-dark-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div className="flex gap-3">
                  <button type="submit" disabled={saving} className="flex-1 bg-brand-600 hover:bg-brand-500 text-white py-2.5 rounded-lg font-medium text-sm transition-colors disabled:opacity-50">
                    {saving ? 'Creating...' : 'Create User'}
                  </button>
                  <button type="button" onClick={() => setShowForm(false)} className="px-5 bg-slate-800 hover:bg-slate-700 text-white py-2.5 rounded-lg text-sm transition-colors">
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
