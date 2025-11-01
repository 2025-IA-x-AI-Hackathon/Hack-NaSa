from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # Startup
    print("🚀 Bluetooth Hybrid API Server Starting...")
    yield
    # Shutdown
    print("🛑 Bluetooth Hybrid API Server Shutting down...")

app = FastAPI(
    title="Bluetooth Hybrid Control API",
    description="macOS Bluetooth 장치 및 미디어 제어 REST API (v2)",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import api.bluetooth  # noqa