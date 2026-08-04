from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.upload import router as upload_router
from app.routes.query import router as query_router
from app.routes.document import router as document_router
from app.database.database import engine
from app.database.models import Base
from app.auth.router import router as auth_router
from app.routes.history import router as history_router

Base.metadata.create_all(
    bind=engine
)

app = FastAPI()

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