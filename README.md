# ADEA - Autonomous Data Engineer Agent

ADEA is an AI-driven data engineering platform that can:

- generate SQL pipelines from natural-language prompts
- execute those pipelines in DuckDB
- monitor failures and anomalies
- diagnose root causes
- repair pipelines with a hybrid LLM + fallback strategy
- retry execution automatically
- suggest optimization improvements
- visualize pipeline lineage and live execution flow

This repo contains both:

- the Python backend (`adea/`)
- the Next.js frontend dashboard (`frontend/`)

## Core Stack

Backend:

- Python 3.11
- FastAPI
- LangGraph
- DuckDB
- SQLAlchemy
- Pydantic
- Groq SDK
- FAISS
- SQLGlot

Frontend:

- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Framer Motion
- React Flow
- Recharts
- SWR
- Zustand

## Project Structure

```text
ADEA/
├─ adea/
│  ├─ agents/
│  ├─ api/
│  ├─ app/
│  ├─ database/
│  ├─ interface/
│  ├─ llm/
│  ├─ memory/
│  ├─ monitoring/
│  ├─ orchestration/
│  ├─ pipelines/
│  └─ utils/
├─ frontend/
│  ├─ app/
│  ├─ components/
│  ├─ hooks/
│  ├─ lib/
│  └─ styles/
├─ requirements.txt
├─ run_adea.py
└─ test_pipeline.py
```

## Before You Start

### 1. Python environment

Create and activate a virtual environment, then install backend dependencies:

```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 2. Frontend dependencies

From the project root:

```powershell
cd frontend
C:\nvm4w\nodejs\npm.cmd install
```

### 3. Environment variables

Create a local `.env` from `.env.example`.

At minimum, if you want live Groq-backed reasoning instead of fallback behavior:

```env
GROQ_API_KEY=your_key_here
```

Notes:

- `.env` is ignored by git
- if `GROQ_API_KEY` is missing or unreachable, ADEA falls back safely to deterministic behavior

### 4. Graphviz

If you want PNG/SVG graph rendering, you need both:

- the Python `graphviz` package
- the Graphviz system binary (`dot`) available on `PATH`

Without the system binary, graph generation may fall back to text/DOT artifacts.

## How To Run

### Backend API

Start the FastAPI server:

```powershell
python -m uvicorn adea.app.main:app --reload
```

Useful URLs:

- Health check: `http://127.0.0.1:8000/health`
- API docs: `http://127.0.0.1:8000/docs`

### Frontend Dashboard

In a new terminal:

```powershell
cd frontend
C:\nvm4w\nodejs\npm.cmd run dev
```

Open:

```text
http://127.0.0.1:3000/dashboard
```

### CLI Interface

Run the interactive CLI:

```powershell
python run_adea.py
```

### Demo Mode

Run the dashboard/CLI demo workflow:

```powershell
python run_adea.py --demo
```

### Backend Test Script

Run the local end-to-end pipeline test:

```powershell
python test_pipeline.py
```

## Typical Workflow For Contributors

1. Start the backend
2. Start the frontend
3. Open the dashboard
4. Run a pipeline prompt such as:

```text
Build sales analytics pipeline
```

5. Watch:

- live agent execution timeline
- pipeline lineage graph
- execution logs
- optimization suggestions
- pipeline history

## Important Notes For Teammates

### Hybrid AI behavior

ADEA is designed as an LLM-first system with safe fallbacks.

That means:

- when Groq is reachable, agents use LLM reasoning
- when Groq fails or times out, deterministic fallback logic keeps the workflow running

### Memory and repair learning

The system stores successful repair experiences and can reuse them for similar failures later.

### Temporary runtime artifacts

Some runtime-generated artifacts may appear during local work, such as:

- pipeline graph files
- temporary DuckDB files
- analyzer reports under `frontend/.next/analyze`

These should not be committed unless intentionally needed.

### Do not commit

Please do not commit:

- `.env`
- `frontend/node_modules`
- `frontend/.next`
- local virtual environments

The repo `.gitignore` already covers these.

## Frontend Performance Tooling

Bundle analyzer:

```powershell
cd frontend
C:\nvm4w\nodejs\npm.cmd run analyze
```

Analyzer reports are generated in:

- `frontend/.next/analyze/client.html`
- `frontend/.next/analyze/nodejs.html`
- `frontend/.next/analyze/edge.html`

There is also a frontend performance guide here:

- [frontend/PERFORMANCE.md](frontend/PERFORMANCE.md)

## Troubleshooting

### Backend starts but frontend cannot load data

Check:

- backend is running on `127.0.0.1:8000`
- frontend is running on `127.0.0.1:3000`
- CORS was not modified

### Groq is not working

Check:

- `GROQ_API_KEY` is set in `.env`
- the machine has internet access
- the Groq SDK is installed from `requirements.txt`

### Graph PNG is not generated

Check:

- Python `graphviz` is installed
- Graphviz system binaries are installed
- `dot` is on your `PATH`

## Collaboration

If you are adding new features:

- keep business logic out of FastAPI routes
- do not change the `PipelineState` structure casually
- keep agent responsibilities isolated
- preserve the LangGraph orchestration flow

The project architecture rules are documented in:

- [AGENTS.md](AGENTS.md)
