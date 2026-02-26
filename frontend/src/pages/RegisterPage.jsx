import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { register as apiRegister } from '../api'
import toast from 'react-hot-toast'

export default function RegisterPage() {
    const [form, setForm] = useState({ username: '', email: '', password: '', role: 'tourist' })
    const [loading, setLoading] = useState(false)
    const { login } = useAuth()
    const navigate = useNavigate()

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        try {
            const res = await apiRegister(form)
            const { access_token, role, user_id } = res.data
            login({ username: form.username, role, user_id }, access_token)
            toast.success('Account created!')
            navigate(role === 'police' ? '/police' : '/tourist')
        } catch (err) {
            toast.error(err.response?.data?.detail || 'Registration failed')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div style={{ textAlign: 'center', marginBottom: 32 }}>
                    <div style={{ fontSize: 48, marginBottom: 16 }}>🧳</div>
                    <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 8 }}>Create Account</h1>
                    <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Join the safety monitoring network</p>
                </div>
                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                    <div className="form-group">
                        <label className="form-label">Username</label>
                        <input className="form-input" type="text" placeholder="Choose a username" value={form.username}
                            onChange={e => setForm({ ...form, username: e.target.value })} required />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Email</label>
                        <input className="form-input" type="email" placeholder="your@email.com" value={form.email}
                            onChange={e => setForm({ ...form, email: e.target.value })} required />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <input className="form-input" type="password" placeholder="Min 8 characters" value={form.password}
                            onChange={e => setForm({ ...form, password: e.target.value })} required />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Role</label>
                        <select className="form-select" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}>
                            <option value="tourist">🧳 Tourist</option>
                            <option value="police">👮 Police Officer</option>
                        </select>
                    </div>
                    <button className="btn btn-primary btn-lg" type="submit" disabled={loading}>
                        {loading ? <><span className="spinner" /> Creating…</> : '✅ Create Account'}
                    </button>
                </form>
                <p style={{ marginTop: 24, textAlign: 'center', color: 'var(--text-secondary)', fontSize: 14 }}>
                    Already have an account?{' '}
                    <Link to="/login" style={{ color: 'var(--accent-blue)', textDecoration: 'none' }}>Sign in</Link>
                </p>
            </div>
        </div>
    )
}
