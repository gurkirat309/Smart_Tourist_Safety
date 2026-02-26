import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import TouristPortal from './pages/TouristPortal'
import PoliceDashboard from './pages/PoliceDashboard'
import Navbar from './components/Navbar'

function ProtectedRoute({ children, requiredRole }) {
    const { user } = useAuth()
    if (!user) return <Navigate to="/login" replace />
    if (requiredRole && user.role !== requiredRole) {
        return <Navigate to={user.role === 'police' ? '/police' : '/tourist'} replace />
    }
    return children
}

function AppRoutes() {
    const { user } = useAuth()
    return (
        <div className="app">
            {user && <Navbar />}
            <div className="main-content">
                <Routes>
                    <Route path="/login" element={!user ? <LoginPage /> : <Navigate to={user.role === 'police' ? '/police' : '/tourist'} />} />
                    <Route path="/register" element={!user ? <RegisterPage /> : <Navigate to="/tourist" />} />
                    <Route path="/tourist" element={
                        <ProtectedRoute requiredRole="tourist">
                            <TouristPortal />
                        </ProtectedRoute>
                    } />
                    <Route path="/police" element={
                        <ProtectedRoute requiredRole="police">
                            <PoliceDashboard />
                        </ProtectedRoute>
                    } />
                    <Route path="/" element={<Navigate to={user ? (user.role === 'police' ? '/police' : '/tourist') : '/login'} />} />
                </Routes>
            </div>
            <Toaster
                position="top-right"
                toastOptions={{
                    style: {
                        background: '#1e293b',
                        color: '#f1f5f9',
                        border: '1px solid #1e3a5f',
                        borderRadius: '10px',
                    }
                }}
            />
        </div>
    )
}

export default function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <AppRoutes />
            </BrowserRouter>
        </AuthProvider>
    )
}
