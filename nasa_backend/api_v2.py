"""
Bluetooth Hybrid API Server (v2)
레이어드 아키텍처 구조:
- Presentation Layer (API Routes)
- Service Layer (Business Logic)
- Repository Layer (Data Access)
- Domain Models (DTOs)

사용 방법:
    uvicorn api_v2:app --reload --host 0.0.0.0 --port 8000

API 문서:
    http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from typing import List, Dict, Optional, Any
from enum import Enum
import asyncio
from contextlib import asynccontextmanager
from bleak import BleakClient

from bluetooth_hybrid_manager import BluetoothHybridManager


# ============================================================================
# Domain Models (DTOs)
# ============================================================================





