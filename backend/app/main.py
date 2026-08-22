from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

from app.routes.upload import router as upload_router
from app.routes.query import router as query_router
from app.routes.document import router as document_router
from app.auth.router import router as auth_router
from app.routes.history import router as history_router
from app.routes.conversations import router as conversations_router
from app.database.database import engine, run_migrations
from app.database.models import Base
from app.core.logging_config import setup_logging


Base.metadata.create_all(bind=engine)
run_migrations()
setup_logging()


app = FastAPI(
    title="Enterprise RAG Assistant API",
    version="1.0.0",
    description="Enterprise-grade RAG pipeline with hybrid search, reranking, and llama3.2 grounding."
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logging.info(
        f"{request.method} {request.url.path} status={response.status_code} time={process_time:.3f}s"
    )
    return response


app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(document_router)
app.include_router(query_router)
app.include_router(history_router)
app.include_router(conversations_router)


@app.get("/")
def home():
    return {
        "status": "healthy",
        "message": "Enterprise RAG Assistant API is running 🚀",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "enterprise-rag-api"
    }


