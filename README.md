# AImail (HTML Frontend + Python Backend)

This bundle contains:
- **frontend/** — static HTML/CSS/JS UI (unchanged layout)
- **backend/** — FastAPI backend that powers login, company profile, templates, AI generation, and refine

## Quick start (local)

### 1) Backend env
Copy:
- `backend/.env.example` → `backend/.env`

Fill at least:
- `OPENAI_API_KEY=...`
- `JWT_SECRET=...` (any random long string)

**Database:** On your machine the app uses **SQLite** (`backend/app.db`) automatically. You do not need Render Postgres locally. On Render, set `DATABASE_URL` in the service environment.

Optional local override: `USE_POSTGRES_LOCALLY=true` to use `DATABASE_URL` from `.env` on your PC.

### 2) Install backend deps
```bash
cd backend
pip install -r requirements.txt
```

### 3) Run
```bash
# from backend/
uvicorn app.main:app --reload --port 8000
```

Open in browser:
- http://localhost:8000/login.html

## Notes
- The frontend uses the same function interface as before (`API.login`, `API.generate`, `API.refine`, ...),
  but now `assets/api.js` calls the real backend endpoints under `/api/*`.
- Login behavior:
  - By default, if the user does not exist it will be auto-created on first login
    (`AUTO_REGISTER_ON_LOGIN=true` in `.env`).
- Company profile is stored per-user in SQLite (`backend/app.db` by default).
- Generated images are returned as **data URIs** (base64) so you don't need object storage for MVP.

## Deploy on Render

1. **Web service**: build e.g. `cd backend && pip install -r requirements.txt`, start e.g. `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
2. **Python version (fixes `pydantic-core` / maturin / read-only cargo errors)**:
   - **Easiest:** In the Render dashboard open your Web Service → **Environment** → add **`PYTHON_VERSION`** = **`3.12.8`** (exact patch form). **Save**, then **Manual Deploy → Clear build cache & deploy**. Render often defaults to **3.14**; `.python-version` is ignored if it was not on the branch you deploy or the cache is stale.
   - **Also:** `backend/requirements.txt` pins **pydantic 2.13.2**, which usually installs a **prebuilt** `pydantic-core` wheel on 3.14 so the Rust step is skipped.
   - **Optional:** Commit **`render.yaml`** and use a **Blueprint**, or keep **`.python-version`** (`3.12.8`) at repo root and under **`backend/`** if the service **Root Directory** is `backend`.
3. **Database**: Use Render Postgres and set **`DATABASE_URL`**; add **`psycopg2-binary`** to `requirements.txt` if you use `postgresql://...` URLs.
4. **Secrets**: Set **`OPENAI_API_KEY`**, **`JWT_SECRET`**, and other vars from `backend/.env.example` in the service **Environment** tab.

## Production next steps (later)
- Move from SQLite to Postgres (`DATABASE_URL=postgresql+psycopg://...`)
- Add Redis + worker queue for heavy generation/sending
- Store images in Cloudflare R2 (or S3) instead of data URIs
- Add click-tracking redirect endpoints (`/r/{token}`) + analytics
