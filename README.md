# ADEA - Autonomous Data Engineer Agent

ADEA is a scaffold for an AI-driven platform that will generate, monitor, repair, and optimize data pipelines.

## Tech Stack

- Python 3.11
- FastAPI
- LangGraph
- DuckDB
- Great Expectations
- FAISS
- SQLAlchemy
- Pydantic
- Uvicorn

## Project Structure

```text
adea/
  app/
  api/
  orchestration/
  agents/
  pipelines/
  monitoring/
  memory/
  database/
  utils/
```

## Development

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
uvicorn adea.app.main:app --reload
```

This repository currently contains architecture scaffolding and placeholders only.
