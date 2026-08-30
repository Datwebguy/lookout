# Lookout: Autonomous Microclimate Heat Safety Agent

* **Live Production Platform:** https://lookoutapp.fly.dev
* **Interactive Operations Dashboard:** https://lookoutapp.fly.dev/app
* **GitHub Repository:** https://github.com/Datwebguy/lookout
* **Project Lead:** @Datweb3guy (https://x.com/Datweb3guy)
* **Core Technology:** FortyGuard Real Time Thermal Intelligence API, FastAPI, OpenAI GPT:4o

---

## 🌟 Executive Summary

Lookout is an autonomous heat safety platform engineered for managers across construction, logistics, agriculture, utilities, and municipal public works. Regional weather apps provide single citywide numbers that fail to capture dangerous localized microclimates. Lookout continuously monitors hyper-local heat stress at exact worksite GPS coordinates using FortyGuard thermal API telemetry.

Lookout calculates personalized worker safety decisions without requiring human prompts:
* **Hyperlocal Thermal Telemetry:** Evaluates real time ground and air microclimate temperatures.
* **Duration Exceedance Analysis:** Calculates cumulative hours spent above dangerous heat thresholds rather than relying on snapshot peaks.
* **Worker Scoped Personalization:** Tailors safety actions based on shift length, sun exposure, heavy PPE gear, and health risk profiles.
* **Autonomous Proactive Alerting:** Automatically schedules rest breaks and dispatches webhooks to Slack and Discord before dangerous heat thresholds are crossed.
* **Multi Tenant Isolation and Security:** Authenticated via official Google OAuth 2.0 with private workspace data isolation and strict PHI PII health data sanitization.

---

## 🏛️ System Architecture

```
                  ┌────────────────────────────────┐
                  │   Autonomous Scheduler Loop    │  Runs continuously in background
                  │   Iterates Registered Sites    │  No human prompt required
                  └────────────────┬───────────────┘
                                   │
                                   ▼
   ┌───────────────┐    ┌────────────────────────┐    ┌──────────────────────┐
   │  FortyGuard   │───▶│  Agent Reasoning Engine│───▶│  Safety Decision     │
   │  API Client   │    │  LLM tool use & signals│    │  Risk tier & action  │
   └───────────────┘    └────────────┬───────────┘    └──────────┬───────────┘
                                     │                           │
                                     ▼                           ▼
                           ┌──────────────────┐        ┌────────────────────┐
                           │ Webhook Dispatch │        │ Audit Decision Log │
                           │ Slack & Discord  │        │ Persisted evidence │
                           └──────────────────┘        └────────────────────┘
```

The system architecture combines real time telemetry with autonomous background execution:
* **FortyGuard SDK Client:** Executes polygon heatmap calls (`POST /v1/heatmap`) and area weights tile data over exact worksite geometries.
* **Autonomous Scheduler:** Executes per-site checks on an active background loop without manual intervention.
* **Reasoning Engine:** Evaluates microclimate telemetry, exceedance duration, and worker risk profiles through structured outputs.
* **Proactive Action Engine:** Detects upcoming threshold crossings using historical analog signals and pre-schedules rest break windows.
* **Multi Channel Alerting:** Dispatches immediate alert notifications to configured Slack and Discord webhooks.

---

## 🚀 Key Feature Suite

### 1. Google OAuth 2.0 Identity & Workspace Isolation
* Authenticates users via official Google Identity Services (GIS).
* Enforces workspace isolation so supervisors only see their own registered worksites and decision logs.

### 2. Autonomous Proactive Protection
* Background threads evaluate all active worksites on regular intervals.
* Pre-schedules mandatory hydration and rest breaks ending exactly when peak heat is projected to hit.

### 3. PHI and PII Health Data Protection
* Medical risk factors remain strictly inside sanitized backend reasoning loops.
* System outputs standardized operational safety tiers (LOW, MODERATE, HIGH, EXTREME) to keep sensitive health records private.

### 4. Interactive Nominatim Address Geocoding
* Translates physical street addresses into accurate GPS coordinates automatically via OpenStreetMap Nominatim.

### 5. Editorial Warm Research Design System
* Styled on an off-white paper canvas (`#f2f8f7`) featuring Source Serif display typography, Inter body sans, IBM Plex Mono eyebrows, and deep teal (`#1c5d5f`) pill controls.

---

## 🛠️ Tech Stack

* **Backend Framework:** Python 3.11, FastAPI, Uvicorn, Python Threading.
* **AI Engine & Telemetry:** FortyGuard API Client (`fortyguard/`), OpenAI GPT:4o.
* **Frontend UI:** HTML5, CSS3 Editorial Design System, Vanilla JavaScript (`web/static/js/app.js`).
* **Cloud Infrastructure:** Fly.io Container Deployment, Depot Docker Builder.

---

## 💻 Local Setup & Installation

### Step 1: Clone Repository
```bash
git clone https://github.com/Datwebguy/lookout.git
cd lookout
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS or Linux
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Credentials
Copy configuration template:
```bash
cp .env.example .env
```

Set your configuration variables:
```env
FORTYGUARD_API_KEY=your_fortyguard_api_key
OPENAI_API_KEY=your_openai_api_key
GOOGLE_CLIENT_ID=your_google_client_id
SLACK_WEBHOOK_URL=your_slack_webhook_url
```

### Step 5: Start Local Web Server
```bash
uvicorn web.server:app --host 127.0.0.1 --port 8001 --reload
```
Navigate to http://127.0.0.1:8001 in your web browser.

---

## 🔬 Automated Verification & Test Scripts

Run the internal proof suite to verify real API integration:

```bash
# Verify FortyGuard Live API Round Trip
python scripts/milestone1_live_proof.py

# Verify Signals Layer & Area Weighted Exceedance
python scripts/milestone2_signals_proof.py

# Verify Autonomous Scheduler & Cache
python scripts/milestone3_scheduler_proof.py

# Verify Agent Reasoning & Personalization
python scripts/milestone4_agent_proof.py

# Verify Proactive Action & Decision Logging
python scripts/milestone5_proactive_proof.py

# Verify Webhook Notification Delivery
python scripts/milestone6_notify_proof.py
```

---

## 📚 FortyGuard API Integration Reference

Lookout leverages FortyGuard's core endpoints:
* `POST /v1/heatmap`: Retrieves thermal tiles and calculates exceedance duration over worksite polygons.
* `POST /v1/env_params`: Fetches apparent temperature, humidity, and solar radiation index.
* `POST /v1/satellite`: Performs land cover segmentation for surface urban heat island analysis.
* `POST /v1/streetview`: Analyzes ground level shading and canopy coverage.
* `POST /v1/heat_intelligence`: Generates structured PDF heat intelligence briefs.

---

© 2026 Lookout. Built on FortyGuard API.
