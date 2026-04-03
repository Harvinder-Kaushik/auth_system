from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app import models
from app.routers import router as auth_router


app = FastAPI(
    title="FastAPI Authentication System",
    description="JWT-based authentication with access + refresh tokens",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Create all tables at startup (simple for local/prototyping use).
    models.Base.metadata.create_all(bind=engine)


app.include_router(auth_router)


@app.get("/", tags=["Health"])
def root() -> dict:
    return {"status": "ok", "message": "Auth API is running"}

