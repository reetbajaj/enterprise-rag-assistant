from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware

from app.routes.upload import router as upload_router
from app.routes.query import router as query_router
from app.routes.document import router as document_router
from app.database.database import engine
from app.database.models import Base
from app.auth.router import router as auth_router
from app.routes.history import router as history_router
from app.core.logging_config import setup_logging
import time
import logging


Base.metadata.create_all(
    bind=engine
)

app = FastAPI()

setup_logging()

@app.middleware("http")
async def log_requests(
    request: Request,
    call_next
):

    start_time = time.time()


    response = await call_next(
        request
    )


    process_time = (
        time.time()
        -
        start_time
    )


    logging.info(
        f"{request.method} "
        f"{request.url.path} "
        f"status={response.status_code} "
        f"time={process_time:.3f}s"
    )


    return response

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(query_router)
app.include_router(document_router)
app.include_router(auth_router)
app.include_router(history_router)

@app.get("/")
def home():
    return {"message": "Enterprise RAG API is running 🚀"}

