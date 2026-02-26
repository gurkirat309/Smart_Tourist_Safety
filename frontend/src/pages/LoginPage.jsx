import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { login as apiLogin } from '../api'
import toast from 'react-hot-toast'

export default function LoginPage() {
    const [form, setForm] = useState({ username: '', password: '' })
    const [loading, setLoading] = useState(false)
    const { login } = useAuth()
    const navigate = useNavigate()

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        try {
            const res = await apiLogin(form)
            const { access_token, role, user_id } = res.data
            login({ username: form.username, role, user_id }, access_token)
            toast.success('Welcome back!')
            navigate(role === 'police' ? '/police' : '/tourist')
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Login failed')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <div style={{ fontSize: 48, marginBottom: 16 }}>🛡️</div>
                    <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 8 }}>Sign In</h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
                        Smart Tourist Safety Monitoring System
                    </p>
                </div>
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                    <div className="form-group">
                        <label className="form-label">Username</label>
                        <input
                            className="form-input"
                            type="text"
                            placeholder="Enter your username"
                            value={form.username}
                            onChange={e => setForm({ ...form, username: e.target.value })}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <input
                            className="form-input"
                            type="password"
                            placeholder="Enter your password"
                            value={form.password}
                            onChange={e => setForm({ ...form, password: e.target.value })}
                            required
                        />
                    </div>
                    <button className="btn btn-primary btn-lg" type="submit" disabled={loading}>
                        {loading ? <><span className="spinner" /> Signing in…</> : '🔐 Sign In'}
                    </button>
                </form>
                <p style={{ marginTop: 24, textAlign: 'center', color: 'var(--text-secondary)', fontSize: 14 }}>
                    No account?{' '}
                    <Link to="/register" style={{ color: 'var(--accent-blue)', textDecoration: 'none' }}>
                        Register here
                    </Link>
                </p>
                <div style={{ marginTop: 16, padding: 14, background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: 8, fontSize: 13, color: 'var(--text-secondary)' }}>
                    👋 <strong style={{ color: 'var(--text-primary)' }}>First time?</strong>{' '}
                    <Link to="/register" style={{ color: 'var(--accent-blue)', textDecoration: 'none' }}>Create an account</Link>{' '}
                    first — there are no pre-built demo accounts.
                </div>
            </div>
        </div>
    )
}
