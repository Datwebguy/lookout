# 🔍 Lookout — Autonomous Microclimate Heat Safety Agent

> **Live Production Platform:** [lookoutapp.fly.dev](https://lookoutapp.fly.dev)  
> **Interactive Dashboard:** [lookoutapp.fly.dev/app](https://lookoutapp.fly.dev/app)  
> **Author & Project Lead:** [@Datweb3guy](https://x.com/Datweb3guy)  
> **Built on:** FortyGuard Real-Time Thermal Intelligence API & FastAPI

---

## 🌟 Overview

**Lookout** is an autonomous heat safety agent designed for managers and supervisors of outdoor workforces (construction, logistics, agriculture, utilities, and municipal public works). Instead of relying on regional weather forecasts, Lookout continuously monitors microclimate heat levels at exact GPS worksite coordinates using real-time [FortyGuard API](https://docs.fortyguard.com) thermal telemetry.

Lookout automatically computes **personalized, worker-scoped safety decisions**:
- **Microclimate Thermal Telemetry:** Evaluates real-time air/ground temperatures and 1-hour forward forecasts.
- **Threshold Exceedance Duration:** Tracks cumulative hours spent above safety limits rather than peak snapshots alone.
- **Worker Risk Profiles:** Tailors recommendations based on shift duration, direct sun exposure, PPE requirements, and health risk flags.
- **Autonomous Dispatch:** Sends automated safety alerts directly to Slack and Discord webhooks without human intervention.
- **Multi-Tenant Isolation & Security:** Scoped by Google Authentication (`GOOGLE_CLIENT_ID`) with multi-tenant workspace data isolation and strict PHI/PII sanitization.

---

## 🚀 Key Features

1. **Google OAuth 2.0 Identity & Gate Screen:**
   - Secure authentication via official Google Identity Services (GIS).
   - Private workspace data isolation — each manager sees only their registered sites and decision log.

2. **Autonomous Background Safety Loop:**
   - A real background thread continuously polls registered sites on an active interval.
   - Triggers automated alerts to Slack & Discord webhooks whenever heat stress risks escalate.

3. **PHI / PII Sanitization:**
   - LLM safety reasoning strictly outputs standardized risk tiers (`LOW`, `MODERATE`, `HIGH`, `EXTREME`) and operational safety phrasing, preventing sensitive worker health information from leaking.

4. **Address Lookup & Microclimate Geocoding:**
   - Interactive OpenStreetMap Nominatim geocoding translates street addresses to exact GPS coordinates (`lat`/`lon`).

5. **Editorial Warm Research Design System:**
   - Built on a warm paper canvas (`#f2f8f7`) with literary serif headlines (`Source Serif 4`), geometric sans body (`Inter`), IBM Plex Mono uppercase eyebrows, and deep teal (`#1c5d5f`) pill CTAs.

---

## 🛠️ Architecture & Tech Stack

- **Backend:** FastAPI (Python 3.11), Uvicorn, Python `threading` background loops, `google-auth`.
- **Telemetry & LLM Reasoning:** FortyGuard API Client (`fortyguard/`), OpenAI GPT-4o safety agent (`lookout/agent.py`).
- **Frontend:** Vanilla JS (`web/static/js/app.js`), HTML5, CSS3 with User Interviews editorial tokens (`web/static/css/styles.css`).
- **Deployment:** Fly.io container deployment (`lookoutapp.fly.dev`), Depot Docker builder.

---

## 💻 Local Setup & Development

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/Datwebguy/lookout.git
cd lookout

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Fill in your environment variables:
```env
FORTYGUARD_API_KEY=your_fortyguard_api_key
OPENAI_API_KEY=your_openai_api_key
GOOGLE_CLIENT_ID=239352907733-6pkm260rhpf8h3hb0sdif7e4dschl8dj.apps.googleusercontent.com
SLACK_WEBHOOK_URL=your_slack_webhook_url
```

### 4. Run the Development Web Server
```bash
uvicorn web.server:app --host 127.0.0.1 --port 8001 --reload
```
Open [http://127.0.0.1:8001](http://127.0.0.1:8001) in your browser!

---

## 📚 FortyGuard API & SDK Reference

The project includes the complete `fortyguard/` SDK package and `notebooks/` walkthroughs for FortyGuard's analysis endpoints:
- `POST /v1/heatmap` — Polygon thermal heatmaps & exceedance analysis.
- `POST /v1/env_params` — Environmental parameters (apparent temp, heat index, AQI, solar radiation).
- `POST /v1/satellite` — Satellite land-cover segmentation.
- `POST /v1/streetview` — Ground-level view segmentation.
- `POST /v1/heat_intelligence` — Heat intelligence PDF report generation.

See [`notebooks/use_cases/README.md`](notebooks/use_cases/README.md) for full narrative notebook workflows.

---

## 🌐 Live Production & Links

- **Live Application:** [https://lookoutapp.fly.dev](https://lookoutapp.fly.dev)
- **Live Dashboard:** [https://lookoutapp.fly.dev/app](https://lookoutapp.fly.dev/app)
- **FortyGuard Documentation:** [https://docs.fortyguard.com](https://docs.fortyguard.com)
- **GitHub Repository:** [https://github.com/Datwebguy/lookout](https://github.com/Datwebguy/lookout)
- **Author X Profile:** [@Datweb3guy](https://x.com/Datweb3guy)

---
© 2026 Lookout. Built on FortyGuard API.
