# HalluciGuard AI

An explainable AI framework for detecting, verifying, and analyzing hallucinations in LLM responses. Enter a question (and optionally an existing AI-generated answer), and HalluciGuard extracts every claim, checks it, and returns a full reliability breakdown: hallucination risk, trust score, verdict, per-claim analysis, highlighted response, evidence, hallucination type, and source-reliability signals.

## Project structure

```
halluciguard-ai/
├── backend/              Flask API + Claude verification engine
│   ├── app.py            Routes: /api/scan, /api/history, /api/benchmark
│   ├── claude_service.py Prompts Claude to answer + audit responses
│   ├── database.py       Supabase Postgres, with local SQLite fallback
│   ├── supabase_schema.sql
│   ├── requirements.txt
│   └── .env.example
└── frontend/             Static dashboard (vanilla HTML/CSS/JS)
    └── index.html
```

## 1. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set at minimum:

```
ANTHROPIC_API_KEY=sk-ant-...
```

By default the backend stores scans in a local SQLite file (`backend/halluciguard.db`) — no extra setup needed. To use Supabase Postgres instead:

1. Create a project at supabase.com.
2. Open the SQL editor and run `backend/supabase_schema.sql`.
3. Copy your Project URL and `service_role` (or `anon`) key into `.env`:
   ```
   SUPABASE_URL=https://xxxx.supabase.co
   SUPABASE_KEY=your-key
   ```

Run it:

```bash
python app.py
```

The API is now live at `http://localhost:5000`.

### Endpoints

| Method | Path             | Description                                    |
|--------|------------------|-------------------------------------------------|
| POST   | `/api/scan`      | `{ question, response? }` → runs the analysis   |
| GET    | `/api/history`   | Returns past scans, most recent first           |
| DELETE | `/api/history`   | Clears all stored scans                         |
| GET    | `/api/benchmark` | Aggregate stats (avg risk, avg trust, etc.)      |
| GET    | `/api/health`    | Health check + which storage backend is active   |

## 2. Frontend setup

The frontend is a single static file — no build step.

For local development, just open `frontend/index.html` in a browser once the backend is running on `localhost:5000` (the default `API_BASE`).

To point it at a deployed backend, set `window.HALLUCIGUARD_API_BASE` before the app scripts run — e.g. add this near the top of `index.html`'s `<body>`:

```html
<script>window.HALLUCIGUARD_API_BASE = "https://your-backend.onrender.com";</script>
```

## 3. Deployment

This mirrors a typical Render (backend) + Vercel (frontend) split:

**Backend → Render**
1. New Web Service, point at the `backend/` folder.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app`
4. Add the environment variables from `.env` in Render's dashboard.

**Frontend → Vercel**
1. Import the repo, set the root directory to `frontend/`.
2. No build step required (static HTML).
3. Set `window.HALLUCIGUARD_API_BASE` to your Render backend URL as shown above.

## Notes

- The "Verification Signals" panel reflects the internal checks HalluciGuard's own model runs (knowledge, consistency, date checks) — it does not call out to other LLM providers, since only Claude is wired up here.
- "Source Reliability" scores are general heuristics about source *categories* (government, research, encyclopedic, unknown), not verified citations for a specific answer.
