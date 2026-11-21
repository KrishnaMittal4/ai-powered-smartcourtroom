# Docker Deployment Guide: AI-Powered Smart Courtroom Backend

This guide documents the containerization of the **AI-Powered Smart Courtroom** FastAPI backend.

---

## 1. Production Architecture Overview

The system architecture preserves the exact production deployment pipeline:

```
┌─────────────────────────────────┐
│              USER               │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│        VERCEL PRODUCTION        │
│    (React / Vite PWA Frontend)  │
│   ai-powered-smartcourtroom.    │
│           vercel.app            │
└────────────────┬────────────────┘
                 │ HTTPS API Calls (VITE_API_BASE)
                 ▼
┌─────────────────────────────────┐
│        RENDER WEB SERVICE       │
│    Docker Container (FastAPI)   │
│   - tesseract-ocr + poppler     │
│   - libgomp1 (OpenMP / FAISS)   │
│   - Non-root user execution     │
│   - Port auto-binding ($PORT)   │
└────────────────┬────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│             EXTERNAL SERVICES & LLM PIPELINE           │
│  - Supabase (Postgres & Storage)                       │
│  - Groq API (High-speed Llama 3 / Mixtral inference)   │
│  - Google Gemini API (Citation Verifier & Bench Judge) │
│  - FAISS + BM25 Hybrid Retrieval + LangGraph CRAG      │
└────────────────────────────────────────────────────────┘
```

> **Important Deployment Confirmations:**
> - **Vercel frontend deployment is 100% preserved.** `VITE_API_BASE` remains pointed to the Render production URL.
> - **No Kubernetes configuration added.** The deployment relies strictly on Docker and Docker Compose.
> - **No secrets baked into Docker images.** All keys and credentials are provided exclusively via runtime environment variables.

---

## 2. Dockerfile Architecture

The [Dockerfile](Dockerfile) uses `python:3.10-slim` (matching the project's `runtime.txt`) and implements key production safeguards:

1. **System Libraries for AI & Document Processing:**
   * `tesseract-ocr`: OCR engine for scanned notices, FIRs, and physical evidence photos.
   * `poppler-utils`: PDF rendering tools (`pdftoppm`, `pdftotext`).
   * `libgomp1`: OpenMP runtime required by `faiss-cpu` for parallel dense vector similarity search.
   * `curl`: Used by the container healthcheck.

2. **Security & Non-Root Execution:**
   * Creates a dedicated non-root user `appuser` (`UID/GID 1000`).
   * Switches to `USER appuser` after permissions are assigned.

3. **Layer Caching Optimization:**
   * Copies `requirements.txt` and runs `pip install --no-cache-dir` *before* copying application code, ensuring instant rebuilds when only code changes.

4. **Dynamic Port Binding & Graceful Shutdown:**
   * Uses `exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`.
   * `exec` ensures Uvicorn runs as PID 1 and receives `SIGTERM` signals directly from Render or Docker for graceful connection draining.

5. **Built-in Healthcheck:**
   * Periodically checks `/health` endpoint to detect hangs or memory spikes.

---

## 3. Docker Compose Configuration

The [docker-compose.yml](docker-compose.yml) file allows one-command local testing of the containerized backend:

```bash
docker compose up --build -d
```

### Key Compose Features:
* Automatically maps ports `8000:8000`.
* Reads environment variables from your local `.env`.
* Mounts local SQLite files (`cases.db`, `feedback.db`, `users.db`) as volumes so local test cases persist across container restarts.
* Runs the container healthcheck every 30 seconds.

---

## 4. Environment Variables Reference

Ensure these runtime variables are configured in Render (or in your local `.env`):

| Variable | Required | Description |
| :--- | :---: | :--- |
| `PORT` | Auto (Render) | Server port (defaults to `8000` locally, set automatically by Render) |
| `GEMINI_API_KEY` | Yes (or Groq) | Google Gemini API key for citation verifier & moot court bench |
| `GROQ_API_KEY` | Yes (or Gemini) | Groq API key for high-speed counsel generation |
| `AUTH_SECRET` | Recommended | Secret key for signing user authentication JWT tokens |
| `SUPABASE_URL` | Optional | Supabase project URL for cloud case storage |
| `SUPABASE_SERVICE_ROLE_KEY` | Optional | Supabase service key for private dossier sync |
| `CORS_ORIGINS` | Recommended | `https://ai-powered-smartcourtroom.vercel.app` |
| `LEXAI_RENDER_FREE_MODE` | Optional | Set to `true` on free tiers to enable zero-RAM Gemini Cloud Embeddings |
| `LEXAI_LOW_MEMORY_MODE` | Optional | Reduces resident memory footprint for 512 MB instances |

---

## 5. Local Docker Commands

### Build the Image Manually
```bash
docker build -t smartcourtroom-backend .
```

### Run the Container
```bash
docker run -d \
  --name smartcourtroom \
  -p 8000:8000 \
  --env-file .env \
  smartcourtroom-backend
```

### Test the Health Endpoint
```bash
curl http://localhost:8000/health
# Response: {"status":"healthy", ...}
```

### View Live Container Logs
```bash
docker logs -f smartcourtroom
```

### Stop the Container
```bash
docker stop smartcourtroom && docker rm smartcourtroom
```

---

## 6. Render Deployment Instructions (Docker Service)

To deploy this container to Render:

1. In the **Render Dashboard**, select your existing `lexai-api` web service (or create a new Web Service).
2. Under **Environment**, switch the runtime to **Docker** (Render will automatically detect `Dockerfile`).
3. Set your **Environment Variables** in the Render Dashboard (under **Environment** tab):
   * `GROQ_API_KEY`
   * `GEMINI_API_KEY`
   * `AUTH_SECRET`
   * `CORS_ORIGINS=https://ai-powered-smartcourtroom.vercel.app`
4. Set **Health Check Path** to `/health`.
5. Trigger **Manual Deploy** $\to$ **Deploy latest commit**.
6. Render will build the Docker container and route traffic to the container port automatically.
