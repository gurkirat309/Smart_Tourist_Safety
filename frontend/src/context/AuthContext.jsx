import { createContext, useContext, useState, useEffect } from 'react'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
    const [user, setUser] = useState(() => {
        try {
            const saved = localStorage.getItem('user')
            return saved ? JSON.parse(saved) : null
        } catch { return null }
    })

    const login = (userData, token) => {
        localStorage.setItem('token', token)
        localStorage.setItem('user', JSON.stringify(userData))
        setUser(userData)
    }

    const logout = () => {
        localStorage.clear()
        setUser(null)
    }

    return <AuthCtx.Provider value={{ user, login, logout }}>{children}</AuthCtx.Provider>
}

export const useAuth = () => useContext(AuthCtx)
