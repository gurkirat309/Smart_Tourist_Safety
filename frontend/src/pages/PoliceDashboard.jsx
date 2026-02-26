import { useState, useEffect, useCallback } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet'
import L from 'leaflet'
import useWebSocket from 'react-use-websocket'
import toast from 'react-hot-toast'
import { listTourists, listAlerts, resolveAlert, listZones, getClusters, getHeatmap, seedZones } from '../api'

const BASE_LAT = 28.6139
const BASE_LNG = 77.2090

function getRiskColor(score) {
    if (score < 0.3) return '#10b981'
    if (score < 0.6) return '#f59e0b'
    if (score < 0.8) return '#ef4444'
    return '#dc2626'
}

function getRiskBg(label) {
    if (label === 0) return 'var(--risk-low)'
    if (label === 1) return 'var(--risk-medium)'
    return 'var(--risk-high)'
}

function makeIcon(color, label = '👤') {
    return L.divIcon({
        className: '',
        html: `<div style="background:${color};width:28px;height:28px;border-radius:50%;
      display:flex;align-items:center;justify-content:center;font-size:14px;
      border:2px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.4);">${label}</div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
    })
}

function HeatmapLayer({ points }) {
    // Simple circles as heatmap (leaflet.heat requires external bundle)
    return points.map((p, i) => (
        <Circle
            key={i}
            center={[p.lat, p.lng]}
            radius={40}
            color={getRiskColor(p.intensity)}
            fillColor={getRiskColor(p.intensity)}
            fillOpacity={0.25}
            weight={0}
        />
    ))
}

function MapUpdater({ center }) {
    const map = useMap()
    useEffect(() => {
        if (center) map.flyTo(center, 14, { animate: true, duration: 1.5 })
    }, [center, map])
    return null
}

export default function PoliceDashboard() {
    const [tourists, setTourists] = useState([])
    const [alerts, setAlerts] = useState([])
    const [zones, setZones] = useState([])
    const [clusters, setClusters] = useState([])
    const [heatmap, setHeatmap] = useState([])
    const [livePositions, setLivePositions] = useState({})  // tourist_id → {lat,lng,risk,name}
    const [selectedTab, setSelectedTab] = useState('map')
    const [mapCenter, setMapCenter] = useState(null)
    const [seeding, setSeeding] = useState(false)

    const { lastJsonMessage } = useWebSocket('ws://localhost:8000/ws/police', {
        onOpen: () => console.log('Police WS connected'),
        shouldReconnect: () => true,
    })

    const loadData = useCallback(async () => {
        try {
            const [tRes, aRes, zRes, cRes, hRes] = await Promise.all([
                listTourists(), listAlerts(), listZones(), getClusters(), getHeatmap()
            ])
            setTourists(tRes.data)
            setAlerts(aRes.data)
            setZones(zRes.data)
            setClusters(cRes.data.clusters || [])
            setHeatmap(hRes.data)
        } catch (e) {
            console.error('Load failed:', e.message)
        }
    }, [])

    useEffect(() => { loadData() }, [loadData])

    // Refresh alerts every 10 seconds
    useEffect(() => {
        const iv = setInterval(() => listAlerts().then(r => setAlerts(r.data)).catch(() => { }), 10000)
        return () => clearInterval(iv)
    }, [])

    useEffect(() => {
        if (!lastJsonMessage) return
        if (lastJsonMessage.event === 'location_update') {
            const { tourist_id, name, lat, lng, composite_risk_score } = lastJsonMessage
            setLivePositions(prev => ({ ...prev, [tourist_id]: { lat, lng, name, risk: composite_risk_score } }))
        }
        if (lastJsonMessage.event === 'alert') {
            const { severity, message } = lastJsonMessage
            if (severity === 'critical') toast.error('🚨 ' + message, { duration: 10000 })
            else if (severity === 'high') toast.error('⚠️ ' + message, { duration: 6000 })
            else toast(message, { icon: '📋', duration: 4000 })
            setAlerts(prev => [lastJsonMessage, ...prev].slice(0, 50))
        }
        if (lastJsonMessage.event === 'cluster_update') {
            setClusters(lastJsonMessage.clusters || [])
        }
    }, [lastJsonMessage])

    const handleResolve = async (alertId) => {
        try {
            await resolveAlert(alertId)
            setAlerts(prev => prev.filter(a => a.id !== alertId))
            toast.success('Alert resolved')
        } catch { toast.error('Failed to resolve') }
    }

    const handleSeedZones = async () => {
        setSeeding(true)
        try {
            const res = await seedZones()
            toast.success(`Zones seeded: ${res.data.count}`)
            loadData()
        } catch { toast.error('Seeding failed') } finally { setSeeding(false) }
    }

    const criticalAlerts = alerts.filter(a => a.severity === 'critical' && !a.is_resolved)
    const highAlerts = alerts.filter(a => a.severity === 'high' && !a.is_resolved)

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)', padding: 16, gap: 16 }}>
            {/* ── Stats ─ */}
            <div className="stat-grid">
                <div className="stat-card">
                    <div className="stat-value">{tourists.length}</div>
                    <div className="stat-label">👥 Active Tourists</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ backgroundImage: 'linear-gradient(135deg,#ef4444,#dc2626)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                        {criticalAlerts.length}
                    </div>
                    <div className="stat-label">🚨 Critical Alerts</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ backgroundImage: 'linear-gradient(135deg,#f59e0b,#d97706)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                        {highAlerts.length}
                    </div>
                    <div className="stat-label">⚠️ High Alerts</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{zones.length}</div>
                    <div className="stat-label">🗺️ Zones Monitored</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{clusters.length}</div>
                    <div className="stat-label">👥 Crowd Clusters</div>
                </div>
                <div className="stat-card" style={{ justifyContent: 'center' }}>
                    <button className="btn btn-secondary btn-sm" onClick={handleSeedZones} disabled={seeding}>
                        {seeding ? <><span className="spinner" /> Seeding…</> : '🌱 Seed Zones'}
                    </button>
                    <button className="btn btn-secondary btn-sm" onClick={loadData} style={{ marginTop: 6 }}>🔄 Refresh</button>
                </div>
            </div>

            {/* ── Main ─ */}
            <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 380px', gap: 16, minHeight: 0 }}>
                {/* Map Area */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <div className="tabs">
                            {['map', 'heatmap'].map(t => (
                                <button key={t} className={`tab ${selectedTab === t ? 'active' : ''}`} onClick={() => setSelectedTab(t)}>
                                    {t === 'map' ? '📍 Live Tracking' : '🔥 Heatmap'}
                                </button>
                            ))}
                        </div>
                        <span className="live-dot" />
                        <span style={{ fontSize: 12, color: 'var(--accent-green)' }}>LIVE</span>
                    </div>
                    <div className="map-container" style={{ flex: 1 }}>
                        <MapContainer center={[BASE_LAT, BASE_LNG]} zoom={14} style={{ height: '100%', width: '100%' }}>
                            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="© OpenStreetMap" />
                            {mapCenter && <MapUpdater center={mapCenter} />}

                            {selectedTab === 'map' && (
                                <>
                                    {/* Live tourist positions */}
                                    {Object.entries(livePositions).map(([id, pos]) => (
                                        <Marker key={id} position={[pos.lat, pos.lng]} icon={makeIcon(getRiskColor(pos.risk), '🧳')}>
                                            <Popup>
                                                <strong>{pos.name}</strong><br />
                                                Risk: {(pos.risk * 100).toFixed(1)}%<br />
                                                📍 {pos.lat.toFixed(5)}, {pos.lng.toFixed(5)}
                                            </Popup>
                                        </Marker>
                                    ))}
                                    {/* Zone circles */}
                                    {zones.map(z => (
                                        <Circle
                                            key={z.id}
                                            center={[z.center_lat, z.center_lng]}
                                            radius={z.radius_km * 1000}
                                            color={getRiskBg(z.risk_label)}
                                            fillColor={getRiskBg(z.risk_label)}
                                            fillOpacity={0.12}
                                            weight={2}
                                        >
                                            <Popup><strong>{z.name}</strong><br />Risk: {['Low', 'Medium', 'High'][z.risk_label]}<br />P: {(z.risk_probability * 100).toFixed(1)}%</Popup>
                                        </Circle>
                                    ))}
                                    {/* DBSCAN crowd clusters */}
                                    {clusters.map(c => (
                                        <Circle
                                            key={c.cluster_id}
                                            center={[c.center_lat, c.center_lng]}
                                            radius={120}
                                            color="#8b5cf6"
                                            fillColor="#8b5cf6"
                                            fillOpacity={0.2}
                                            weight={2}
                                        >
                                            <Popup>👥 Cluster #{c.cluster_id}<br />Tourists: {c.tourist_count}<br />Risk: {(c.crowd_risk * 100).toFixed(0)}%</Popup>
                                        </Circle>
                                    ))}
                                </>
                            )}

                            {selectedTab === 'heatmap' && <HeatmapLayer points={heatmap} />}
                        </MapContainer>
                    </div>
                </div>

                {/* Sidebar */}
                <div className="sidebar">
                    {/* Tourist List */}
                    <div className="card">
                        <div className="section-title">Live Tourists</div>
                        {tourists.length === 0 ? (
                            <div className="empty-state"><div className="empty-state-icon">👥</div><p>No tourists registered yet</p></div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                {tourists.map(t => {
                                    const pos = livePositions[t.id]
                                    return (
                                        <div key={t.id} className="tourist-list-item"
                                            onClick={() => pos && setMapCenter([pos.lat, pos.lng])}>
                                            <div className="tourist-avatar">{t.name[0].toUpperCase()}</div>
                                            <div style={{ flex: 1, minWidth: 0 }}>
                                                <div style={{ fontWeight: 600, fontSize: 14 }}>{t.name}</div>
                                                {pos ? (
                                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                                                        Risk: {(pos.risk * 100).toFixed(0)}%
                                                    </div>
                                                ) : (
                                                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Offline</div>
                                                )}
                                            </div>
                                            {pos && <div style={{ width: 8, height: 8, borderRadius: '50%', background: getRiskColor(pos.risk) }} />}
                                        </div>
                                    )
                                })}
                            </div>
                        )}
                    </div>

                    {/* Alert Panel */}
                    <div className="card">
                        <div className="section-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span>Active Alerts</span>
                            <span style={{ fontSize: 12, background: 'var(--accent-red)', color: 'white', borderRadius: 100, padding: '2px 8px' }}>
                                {alerts.filter(a => !a.is_resolved).length}
                            </span>
                        </div>
                        {alerts.filter(a => !a.is_resolved).length === 0 ? (
                            <div className="empty-state"><div className="empty-state-icon">✅</div><p>All clear</p></div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 400, overflowY: 'auto' }}>
                                {alerts.filter(a => !a.is_resolved).map((a, i) => (
                                    <div key={a.id || i} className={`alert-item ${a.severity}`}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                            <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                                                {a.severity} · {a.alert_type}
                                            </span>
                                            {a.id && (
                                                <button className="btn btn-secondary btn-sm" style={{ padding: '2px 8px', fontSize: 11 }}
                                                    onClick={() => handleResolve(a.id)}>
                                                    ✓ Resolve
                                                </button>
                                            )}
                                        </div>
                                        <div style={{ fontSize: 13 }}>{a.message}</div>
                                        {a.created_at && (
                                            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                                                {new Date(a.created_at).toLocaleTimeString()}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Crowd Clusters */}
                    <div className="card">
                        <div className="section-title">Crowd Clusters</div>
                        {clusters.length === 0 ? (
                            <div className="empty-state"><div className="empty-state-icon">👥</div><p>No dense clusters detected</p></div>
                        ) : (
                            clusters.map(c => (
                                <div key={c.cluster_id} style={{
                                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                    padding: '10px 0', borderBottom: '1px solid var(--border)', cursor: 'pointer'
                                }} onClick={() => setMapCenter([c.center_lat, c.center_lng])}>
                                    <div>
                                        <div style={{ fontWeight: 600, fontSize: 14 }}>Cluster #{c.cluster_id}</div>
                                        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{c.tourist_count} tourists · {c.center_lat.toFixed(4)}, {c.center_lng.toFixed(4)}</div>
                                    </div>
                                    <div style={{ color: getRiskColor(c.crowd_risk), fontWeight: 700, fontSize: 14 }}>
                                        {(c.crowd_risk * 100).toFixed(0)}%
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    {/* Zone Risk Table */}
                    <div className="card">
                        <div className="section-title">Zone Risk Overview</div>
                        {zones.length === 0 ? (
                            <div className="empty-state"><div className="empty-state-icon">🗺️</div><p>No zones seeded yet. Click "Seed Zones".</p></div>
                        ) : (
                            zones.map(z => (
                                <div key={z.id} style={{
                                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                    padding: '8px 0', borderBottom: '1px solid var(--border)', cursor: 'pointer'
                                }} onClick={() => setMapCenter([z.center_lat, z.center_lng])}>
                                    <div>
                                        <div style={{ fontWeight: 500, fontSize: 13 }}>{z.name}</div>
                                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{z.zone_type}</div>
                                    </div>
                                    <span className={`badge badge-${z.risk_label === 0 ? 'low' : z.risk_label === 1 ? 'medium' : 'high'}`}>
                                        {['Low', 'Medium', 'High'][z.risk_label]}
                                    </span>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
