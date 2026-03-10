import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Wifi, KeyRound, Mail, AlertCircle, Server } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || '/api'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [debugInfo, setDebugInfo] = useState(null)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setDebugInfo(null)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail
      const msg = err.message

      setError(detail || msg || 'Login failed')
      setDebugInfo({
        api_url: API_URL,
        status: status || 'No response (network error)',
        detail: detail || 'none',
        message: msg,
      })
    } finally {
      setLoading(false)
    }
  }

  const testBackend = async () => {
    try {
      const res = await fetch(`${API_URL}/health`)
      const data = await res.json()
      setDebugInfo({ api_url: API_URL, health: data, status: res.status })
    } catch (err) {
      setDebugInfo({ api_url: API_URL, error: err.message, status: 'FAILED' })
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-950 relative overflow-hidden">
      <div className="absolute inset-0 opacity-5"
        style={{ backgroundImage: 'linear-gradient(#0ea5e9 1px, transparent 1px), linear-gradient(90deg, #0ea5e9 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-brand-600/20 rounded-full blur-3xl" />

      <div className="relative w-full max-w-md px-6">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand-600/20 border border-brand-500/30 mb-4">
            <Wifi className="w-8 h-8 text-brand-400" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Hotel Hotspot</h1>
          <p className="text-slate-400 mt-1 text-sm">Automation & Management System</p>
        </div>

        <div className="card p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                  className="w-full bg-dark-900 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
                  placeholder="admin@hotel.com" required />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 block">Password</label>
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                  className="w-full bg-dark-900 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
                  placeholder="••••••••" required />
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {debugInfo && (
              <div className="text-xs bg-slate-900 border border-slate-700 rounded-lg p-3 font-mono text-slate-400 space-y-1">
                {Object.entries(debugInfo).map(([k, v]) => (
                  <div key={k}><span className="text-slate-500">{k}:</span> <span className="text-yellow-400">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span></div>
                ))}
              </div>
            )}

            <button type="submit" disabled={loading}
              className="w-full bg-brand-600 hover:bg-brand-500 text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-50 text-sm tracking-wide">
              {loading ? 'Signing in...' : 'Sign In'}
            </button>

            <button type="button" onClick={testBackend}
              className="w-full flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white py-2 rounded-lg transition-colors text-xs">
              <Server className="w-3 h-3" />
              Test Backend Connection
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-slate-600 mt-4">
          API: <span className="text-slate-500 font-mono">{API_URL}</span>
        </p>
      </div>
    </div>
  )
}
