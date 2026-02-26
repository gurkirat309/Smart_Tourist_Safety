import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
})

api.interceptors.response.use(
    (r) => r,
    (err) => {
        if (err.response?.status === 401) {
            localStorage.clear()
            window.location.href = '/login'
        }
        return Promise.reject(err)
    }
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const register = (data) => api.post('/auth/register', data)
export const login = (data) => api.post('/auth/login', data)

// ── Tourist ───────────────────────────────────────────────────────────────────
export const getTouristProfile = () => api.get('/tourist/profile')
export const startRoute = (data) => api.post('/tourist/route/start', data)
export const updateLocation = (data) => api.post('/tourist/location/update', data)
export const getRiskStatus = () => api.get('/tourist/risk-status')
export const triggerPanic = () => api.post('/tourist/panic')

// ── Police ────────────────────────────────────────────────────────────────────
export const listTourists = () => api.get('/police/tourists')
export const listAlerts = (resolved = false) => api.get(`/police/alerts?resolved=${resolved}`)
export const resolveAlert = (id) => api.post(`/police/alerts/${id}/resolve`)
export const listZones = () => api.get('/police/zones')
export const getClusters = () => api.get('/police/crowd/clusters')
export const getHeatmap = () => api.get('/police/heatmap')
export const seedZones = () => api.post('/police/seed-zones')

export default api
