# Label Police Backend

FastAPI service for packaging-label OCR and Indian Legal Metrology (Packaged Commodities) Rule 6 checks.

## Local setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/docs

Set one vision key in `backend/.env`: `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, or `OPENAI_API_KEY`. OpenRouter is preferred when configured and defaults to `google/gemma-4-31b-it:free`, a vision-capable model. If no key is set, `POST /api/v1/scans/analyze` returns a structured mock extraction instead of a 500 error. The mock is then scored by the rules engine so the API remains testable without cloud credentials.

## Database

Set `DATABASE_URL` in `backend/.env` for PostgreSQL persistence, for example:

```text
DATABASE_URL=postgresql://label_police:password@localhost:5432/label_police
```

Tables are created when FastAPI starts. Without `DATABASE_URL`, the local SQLite database remains available for development.

## Analyze a label

```bash
curl -X POST http://localhost:8000/api/v1/scans/analyze -F "file=@label.jpg"
```

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/health` | Process health |
| POST | `/api/v1/scans/analyze` | Upload a label image and receive compliance results |
| GET | `/api/v1/scans` | Recent saved scans, newest first |
| GET | `/api/v1/rules` | Legal Metrology guideline catalog |
| POST | `/api/v1/auth/register` | Create an account |
| POST | `/api/v1/auth/login` | Issue JWT access and refresh tokens |
| POST | `/api/v1/auth/refresh` | Rotate tokens |

## Tests

```bash
cd backend
pytest
```

## Railway deployment

Deploy the `backend` directory as a Railway service. The included `Dockerfile` and
`railway.toml` install the Python dependencies, bind Uvicorn to Railway's assigned
`PORT`, and use `/api/v1/health` as the health check. Add `OPENROUTER_API_KEY`,
`OPENROUTER_MODEL`, and a strong `SECRET_KEY` in Railway's Variables page. After
Railway generates a public domain, put `https://YOUR-DOMAIN/api/v1` in
`mobile/.env` as `EXPO_PUBLIC_API_URL`, then restart Expo in tunnel mode.
