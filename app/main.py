import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app import models
from app.routers import router as auth_router
from app.rate_limit import limiter, add_rate_limit_exception_handler

# Load environment variables
load_dotenv()

app = FastAPI(
    title="FastAPI Authentication System",
    description="JWT-based authentication with access + refresh tokens",
    version="1.0.0",
)

# Parse allowed origins from environment variable
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
allowed_origins = [origin.strip() for origin in allowed_origins]

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Add rate limit exception handler
add_rate_limit_exception_handler(app)


@app.on_event("startup")
def on_startup() -> None:
    # Create all tables at startup (simple for local/prototyping use).
    models.Base.metadata.create_all(bind=engine)


app.include_router(auth_router)


@app.get("/", tags=["Health"])
def root() -> dict:
    return {"status": "ok", "message": "Auth API is running"}

