from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import init_db
from app.db.redis import init_redis, close_redis
from app.db.chroma import init_chroma
from app.api.auth import router as auth_router
from app.api.search import router as search_router
from app.api.chat import router as chat_router
from app.api.mcp import router as mcp_router
from app.api.voice import router as voice_router
from app.api.report import router as report_router
from app.api.patient import router as patient_router
from app.api.doctor import router as doctor_router
from app.api.kb import router as kb_router
from app.api.registration import router as registration_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_redis()
    await init_chroma()
    yield
    await close_redis()


app = FastAPI(
    title="医患双端服务平台 API",
    description="面向医患双端的一体化智能医学 Agent 平台",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


app.include_router(auth_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(mcp_router)
app.include_router(voice_router)
app.include_router(report_router)
app.include_router(patient_router)
app.include_router(doctor_router)
app.include_router(kb_router)
app.include_router(registration_router)
