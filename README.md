# FastAPI Authentication System

JWT-based authentication with access + refresh tokens.

## Run

```bash
# cd auth_system
# (venv) pip install -r requirements.txt
python run.py
# or: uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`

## Configuration

Set `JWT_SECRET_KEY` (recommended) before deploying.

