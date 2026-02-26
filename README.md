# Smart Tourist Safety Monitoring & Incident Response System

A full-stack AI-powered web application that monitors tourists in real-time using 4 ML models.

## Project Structure

```
Smart tourist safety/
├── backend/
│   ├── pyproject.toml          # uv dependencies
│   ├── .env.example            # Copy to .env
│   └── app/
│       ├── main.py             # FastAPI entry point
│       ├── config.py           # Settings
│       ├── database.py         # SQLAlchemy session
│       ├── auth.py             # JWT auth
│       ├── schemas.py          # Pydantic schemas
│       ├── models/             # SQLAlchemy ORM models
│       ├── ml_models/          # 4 ML models
│       │   ├── area_risk.py    # Random Forest classifier
│       │   ├── route_deviation.py  # Isolation Forest
│       │   ├── inactivity.py   # Gradient Boosting
│       │   └── crowd_density.py    # DBSCAN clustering
│       ├── services/
│       │   ├── data_generator.py   # Synthetic dataset generator
│       │   ├── alert_engine.py     # Alert logic
│       │   └── websocket_manager.py # WS connections
│       └── routes/
│           ├── auth.py         # Register / Login
│           ├── tourist.py      # Tourist APIs
│           ├── police.py       # Police APIs
│           └── websocket.py    # WS endpoints
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx, main.jsx, index.css
        ├── api.js              # Axios client
        ├── context/AuthContext.jsx
        ├── components/Navbar.jsx
        └── pages/
            ├── LoginPage.jsx
            ├── RegisterPage.jsx
            ├── TouristPortal.jsx   # Tourist dashboard
            └── PoliceDashboard.jsx # Police dashboard
```

## Prerequisites

- **Python 3.11+** with [uv](https://docs.astral.sh/uv/) installed
- **Node.js 18+** with npm
- **PostgreSQL** running locally (or update DATABASE_URL in .env)

## Backend Setup

```bash
cd "Smart tourist safety/backend"

# 1. Copy .env
copy .env.example .env
# Edit .env: update DATABASE_URL with your PostgreSQL credentials

# 2. Create the database in PostgreSQL
# psql -U postgres -c "CREATE DATABASE tourist_safety;"

# 3. Install dependencies
uv sync

# 4. Start the server (tables auto-created on startup, ML models auto-trained)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access Swagger UI: http://localhost:8000/docs

## Frontend Setup

```bash
cd "Smart tourist safety/frontend"

# 1. Install dependencies
npm install

# 2. Start dev server
npm run dev
```

Open: http://localhost:5173

## First Run Steps

1. Start backend → visit `/docs`
2. Register a **police** account via `/api/auth/register`
3. Call `POST /api/police/seed-zones` (or click "🌱 Seed Zones" in dashboard) to populate zones
4. ML models auto-train on first startup using synthetic data — this may take ~30s
5. Register a **tourist** account and open Tourist Portal
6. Click "🚀 Start Route & Tracking" — location simulation begins (4-second intervals)
7. Watch the Police Dashboard update in real-time via WebSockets

## ML Models

| Model | Algorithm | Training Data |
|-------|-----------|---------------|
| Area Risk | RandomForest (supervised) | 3000 synthetic zone observations |
| Route Deviation | IsolationForest (anomaly detection) | 1800 movement pings (1500 normal + 300 anomalous) |
| Inactivity | GradientBoosting (supervised) | 3000 inactivity scenarios |
| Crowd Density | DBSCAN (clustering) | Run at inference time on live pings |

All training data is generated internally in `app/services/data_generator.py`. No external APIs used.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register tourist/police |
| POST | `/api/auth/login` | Login → JWT |
| GET | `/api/tourist/profile` | Get tourist profile |
| POST | `/api/tourist/route/start` | Start a route |
| POST | `/api/tourist/location/update` | Update location (runs all 4 ML models) |
| GET | `/api/tourist/risk-status` | Get current risk assessment |
| POST | `/api/tourist/panic` | Trigger emergency panic alert |
| GET | `/api/police/tourists` | List all tourists |
| GET | `/api/police/alerts` | List all alerts |
| POST | `/api/police/alerts/{id}/resolve` | Resolve an alert |
| GET | `/api/police/zones` | List all zones |
| GET | `/api/police/crowd/clusters` | Get DBSCAN cluster summaries |
| GET | `/api/police/heatmap` | Get heatmap data |
| POST | `/api/police/seed-zones` | Seed synthetic zones |
| WS | `/ws/police` | Police dashboard WebSocket |
| WS | `/ws/tourist/{id}` | Tourist live updates WebSocket |

## Alert Logic

| Condition | Severity |
|-----------|----------|
| High area risk + route deviation | 🔴 Critical |
| Suspicious inactivity in risky zone | 🟠 High |
| Crowd density > 80% | 🟠 High |
| Tourist in high-risk zone | 🟡 Medium |
| Route deviation only | 🟡 Medium |
| Panic button pressed | 🔴 Critical |
