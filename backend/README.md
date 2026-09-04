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

If `GEMINI_API_KEY` and `OPENAI_API_KEY` are empty, `POST /api/v1/scans/analyze` returns a structured mock extraction instead of a 500 error. The mock is then scored by the rules engine so the API remains testable without cloud credentials.

## Analyze a label

```bash
curl -X POST http://localhost:8000/api/v1/scans/analyze -F "file=@label.jpg"
```

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/health` | Process health |
| POST | `/api/v1/scans/analyze` | Upload a label image and receive compliance results |
| GET | `/api/v1/rules` | Legal Metrology guideline catalog |
| POST | `/api/v1/auth/register` | Create an account |
| POST | `/api/v1/auth/login` | Issue JWT access and refresh tokens |
| POST | `/api/v1/auth/refresh` | Rotate tokens |

## Tests

```bash
cd backend
pytest
```
