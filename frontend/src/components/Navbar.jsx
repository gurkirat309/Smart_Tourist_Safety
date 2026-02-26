import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
    const { user, logout } = useAuth()
    const navigate = useNavigate()

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

    return (
        <nav className="navbar">
            <div className="navbar-brand">
                <div className="navbar-brand-icon">🛡️</div>
                Smart Tourist Safety
            </div>
            <div className="navbar-actions">
                {user && (
                    <>
                        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                            {user.role === 'police' ? '👮' : '🧳'} {user.username}
                        </span>
                        <span className={`badge badge-${user.role === 'police' ? 'medium' : 'low'}`}>
                            {user.role}
                        </span>
                        <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
                            Logout
                        </button>
                    </>
                )}
            </div>
        </nav>
    )
}
