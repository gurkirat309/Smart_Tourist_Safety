import { useState, useEffect, useRef, useCallback } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, Circle, useMap } from 'react-leaflet'
import L from 'leaflet'
import useWebSocket from 'react-use-websocket'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import { startRoute, updateLocation, getRiskStatus, triggerPanic } from '../api'

const BASE_LAT = 28.6139
const BASE_LNG = 77.2090

// Custom tourist marker
const touristIcon = L.divIcon({
    className: '',
    html: `<div style="
    width:32px;height:32px;background:linear-gradient(135deg,#3b82f6,#06b6d4);
    border-radius:50% 50% 50% 0;transform:rotate(-45deg);
    border:3px solid white;box-shadow:0 2px 12px rgba(59,130,246,0.5);
  "></div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
})

function getRiskColor(score) {
    if (score < 0.3) return '#10b981'
    if (score < 0.6) return '#f59e0b'
    if (score < 0.8) return '#ef4444'
    return '#dc2626'
}

function RiskMeter({ score }) {
    const color = getRiskColor(score)
    const label = score < 0.3 ? 'LOW' : score < 0.6 ? 'MEDIUM' : score < 0.8 ? 'HIGH' : 'CRITICAL'
    const badgeClass = score < 0.3 ? 'badge-low' : score < 0.6 ? 'badge-medium' : 'badge-high'
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Composite Risk Score</span>
                <span className={`badge ${badgeClass}`}>{label}</span>
            </div>
            <div className="risk-meter">
                <div className="risk-meter-fill" style={{ width: `${Math.round(score * 100)}%`, background: `linear-gradient(90deg, ${color}aa, ${color})` }} />
            </div>
            <div style={{ fontSize: 28, fontWeight: 800, color }}>{(score * 100).toFixed(1)}%</div>
        </div>
    )
}

function MapCenter({ lat, lng }) {
    const map = useMap()
    useEffect(() => {
        if (lat && lng) map.setView([lat, lng], 15, { animate: true })
    }, [lat, lng, map])
    return null
}

export default function TouristPortal() {
    const { user } = useAuth()
    const [position, setPosition] = useState([BASE_LAT, BASE_LNG])
    const [riskStatus, setRiskStatus] = useState(null)
    const [alerts, setAlerts] = useState([])
    const [routeActive, setRouteActive] = useState(false)
    const [waypoints, setWaypoints] = useState([])
    const [tracking, setTracking] = useState(false)
    const [panicSent, setPanicSent] = useState(false)
    const watchId = useRef(null)
    const simulationRef = useRef(null)

    const wsUrl = `ws://localhost:8000/ws/tourist/${user?.user_id}`
    const { lastJsonMessage } = useWebSocket(wsUrl, {
        onOpen: () => console.log('Tourist WS connected'),
        shouldReconnect: () => true,
    })

    useEffect(() => {
        if (!lastJsonMessage) return
        if (lastJsonMessage.event === 'alert') {
            const { severity, message } = lastJsonMessage
            if (severity === 'critical') toast.error('🚨 ' + message, { duration: 8000 })
            else if (severity === 'high') toast.error('⚠️ ' + message, { duration: 5000 })
            else toast(message, { icon: '⚠️', duration: 4000 })
            setAlerts(prev => [lastJsonMessage, ...prev].slice(0, 20))
        }
        if (lastJsonMessage.event === 'location_update') {
            setRiskStatus(s => s ? { ...s, composite_risk_score: lastJsonMessage.composite_risk_score } : s)
        }
    }, [lastJsonMessage])

    // Simulate location (since we can't use real GPS in browser without https)
    const startSimulation = useCallback(() => {
        let step = 0
        const path = Array.from({ length: 40 }, (_, i) => [
            BASE_LAT + (i * 0.0005) + Math.random() * 0.0002,
            BASE_LNG + (i * 0.0003) + Math.random() * 0.0002,
        ])
        setWaypoints(path)

        simulationRef.current = setInterval(async () => {
            if (step >= path.length) { step = 0 }
            const [lat, lng] = path[step]
            setPosition([lat, lng])
            step++
            try {
                await updateLocation({ lat, lng })
                const res = await getRiskStatus()
                setRiskStatus(res.data)
            } catch (err) {
                console.error('Location update failed:', err.message)
            }
        }, 4000)
        setTracking(true)
        toast.success('📍 Live tracking started')
    }, [])

    const stopSimulation = () => {
        if (simulationRef.current) clearInterval(simulationRef.current)
        setTracking(false)
        toast('📍 Tracking stopped', { icon: '⏹' })
    }

    const handleStartRoute = async () => {
        const route = {
            start_lat: BASE_LAT,
            start_lng: BASE_LNG,
            end_lat: BASE_LAT + 0.02,
            end_lng: BASE_LNG + 0.015,
            planned_waypoints: JSON.stringify(
                Array.from({ length: 10 }, (_, i) => [BASE_LAT + i * 0.002, BASE_LNG + i * 0.0015])
            ),
        }
        try {
            await startRoute(route)
            setRouteActive(true)
            toast.success('🗺️ Route started!')
            startSimulation()
        } catch {
            toast.error('Failed to start route')
        }
    }

    const handlePanic = async () => {
        try {
            await triggerPanic()
            setPanicSent(true)
            toast.error('🚨 PANIC ALERT SENT TO POLICE!', { duration: 10000 })
        } catch {
            toast.error('Failed to send panic alert')
        }
    }

    const riskScore = riskStatus?.composite_risk_score ?? 0

    return (
        <div className="dashboard">
            {/* ── Map ─────────────────────────────────────────────────────── */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <h2 style={{ fontSize: 18, fontWeight: 700 }}>🗺️ Live Map</h2>
                    {tracking && <><span className="live-dot" /> <span style={{ fontSize: 12, color: 'var(--accent-green)' }}>LIVE</span></>}
                </div>
                <div className="map-container" style={{ flex: 1 }}>
                    <MapContainer center={position} zoom={15} style={{ height: '100%', width: '100%' }}>
                        <TileLayer
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                            attribution="© OpenStreetMap contributors"
                        />
                        <MapCenter lat={position[0]} lng={position[1]} />
                        {/* Tourist position */}
                        <Marker position={position} icon={touristIcon}>
                            <Popup>📍 Your Location<br />Risk: {(riskScore * 100).toFixed(1)}%</Popup>
                        </Marker>
                        {/* Planned route */}
                        {waypoints.length > 1 && (
                            <Polyline positions={waypoints} color="#3b82f6" weight={3} opacity={0.7} dashArray="8,4" />
                        )}
                        {/* Risk radius circle */}
                        <Circle
                            center={position}
                            radius={150}
                            color={getRiskColor(riskScore)}
                            fillColor={getRiskColor(riskScore)}
                            fillOpacity={0.1}
                            weight={2}
                        />
                    </MapContainer>
                </div>
            </div>

            {/* ── Sidebar ──────────────────────────────────────────────────── */}
            <div className="sidebar">
                {/* Risk Score */}
                <div className="card">
                    <div className="section-title">Risk Status</div>
                    <RiskMeter score={riskScore} />
                    {riskStatus && (
                        <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {[
                                { label: 'Area Risk', value: riskStatus.area_risk_label, icon: '🏙️' },
                                { label: 'Deviated from route', value: riskStatus.is_deviation ? 'YES ⚠️' : 'No ✅', icon: '📍' },
                                { label: 'Inactivity', value: `${riskStatus.inactivity_minutes?.toFixed(1) ?? 0} min`, icon: '⏱️' },
                                { label: 'Crowd Risk', value: `${((riskStatus.crowd_risk ?? 0) * 100).toFixed(0)}%`, icon: '👥' },
                            ].map(({ label, value, icon }) => (
                                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                                    <span style={{ color: 'var(--text-secondary)' }}>{icon} {label}</span>
                                    <span style={{ fontWeight: 600 }}>{value}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Controls */}
                <div className="card">
                    <div className="section-title">Route Controls</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        {!routeActive ? (
                            <button className="btn btn-primary" onClick={handleStartRoute}>
                                🚀 Start Route & Tracking
                            </button>
                        ) : tracking ? (
                            <button className="btn btn-secondary" onClick={stopSimulation}>⏹ Stop Tracking</button>
                        ) : (
                            <button className="btn btn-success" onClick={startSimulation}>▶️ Resume Tracking</button>
                        )}
                    </div>
                </div>

                {/* PANIC BUTTON */}
                <div className="card">
                    <div className="section-title">Emergency</div>
                    <button
                        className="panic-button"
                        onClick={handlePanic}
                        disabled={panicSent}
                        style={panicSent ? { opacity: 0.7, cursor: 'not-allowed' } : {}}
                    >
                        {panicSent ? '🚨 ALERT SENT' : '🆘 PANIC — SEND EMERGENCY ALERT'}
                    </button>
                    <p style={{ marginTop: 10, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
                        Instantly notifies all police officers on duty
                    </p>
                </div>

                {/* Alerts */}
                <div className="card">
                    <div className="section-title">My Alerts ({alerts.length})</div>
                    {alerts.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-state-icon">✅</div>
                            <p>No active alerts. Stay safe!</p>
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 300, overflowY: 'auto' }}>
                            {alerts.map((a, i) => (
                                <div key={i} className={`alert-item ${a.severity}`}>
                                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 4 }}>
                                        {a.severity} · {a.alert_type}
                                    </div>
                                    <div style={{ fontSize: 13 }}>{a.message}</div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
